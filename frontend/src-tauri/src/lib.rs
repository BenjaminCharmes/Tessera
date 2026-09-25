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
            "uvicorn",
            "tessera.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
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
