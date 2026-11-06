use std::process::{Child, Command};
use std::sync::Mutex;

// Backend directory resolved at compile time from the Cargo.toml location. It is only a
// fallback: a packaged app lives far from the source tree, so `TESSERA_BACKEND_DIR` wins.
const BACKEND_DIR: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../../backend");

fn backend_dir() -> String {
    std::env::var("TESSERA_BACKEND_DIR").unwrap_or_else(|_| BACKEND_DIR.to_owned())
}

// Spawns the FastAPI backend process. Only called in release builds; in dev mode the user
// runs `make dev` separately (or `make run` to start both in one terminal).
//
// No shell in between: `sh` does not exist on Windows, and listing the arguments keeps the
// command line out of anyone's reach. The backend binds the loopback interface only — the
// desktop shell is its sole client, and `routers/fs.py` is the only door to the disk.
fn spawn_backend() -> Option<Child> {
    let dir = backend_dir();
    let spawned = Command::new("uv")
        .args([
            "run",
            "python",
            "-m",
            "uvicorn",
            "tessera.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8100",
            "--env-file",
            "../.env",
        ])
        .current_dir(&dir)
        .spawn();
    match spawned {
        Ok(child) => Some(child),
        Err(err) => {
            eprintln!("tessera: failed to spawn the backend from {dir}: {err}");
            None
        }
    }
}

// Session token written by the backend at each start, read here so the webview never
// holds it in its bundle. Same location as `default_state_dir` in the backend's config.
fn token_path() -> Result<std::path::PathBuf, String> {
    let (var, tail) = if cfg!(windows) {
        ("LOCALAPPDATA", "Tessera/jeton-de-session")
    } else {
        ("HOME", ".local/state/tessera/jeton-de-session")
    };
    let base = std::env::var_os(var).ok_or_else(|| format!("{var} is not set"))?;
    Ok(std::path::PathBuf::from(base).join(tail))
}

// No `fs` plugin (ADR-040): one command, one file.
#[tauri::command]
fn jeton_de_session() -> Result<String, String> {
    let path = token_path()?;
    std::fs::read_to_string(&path)
        .map(|content| content.trim().to_owned())
        .map_err(|err| format!("{}: {err}", path.display()))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // In dev mode (debug build) the user starts the backend with `make dev` or `make run`.
    // In release mode the app spawns and owns the backend process.
    let backend_process: Mutex<Option<Child>> = Mutex::new(if cfg!(debug_assertions) {
        None
    } else {
        spawn_backend()
    });

    let app = tauri::Builder::default()
        // System notifications when a run needs someone (ticket-200). Its only
        // capability is `notification:default`; nothing reaches the disk.
        .plugin(tauri_plugin_notification::init())
        .invoke_handler(tauri::generate_handler![jeton_de_session])
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(move |_handle, event| {
        if let tauri::RunEvent::Exit = event {
            if let Ok(mut guard) = backend_process.lock() {
                if let Some(mut child) = guard.take() {
                    let _ = child.kill();
                }
            }
        }
    });
}
