use std::fs;
use std::process::Child;
use std::sync::Mutex;
use tauri::command;

// Path to the backend directory, resolved at compile time from the Cargo.toml location.
const BACKEND_DIR: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../../backend");

#[command]
fn read_file(path: String) -> Result<String, String> {
    fs::read_to_string(&path).map_err(|e| format!("Failed to read {path}: {e}"))
}

#[command]
fn write_file(path: String, content: String) -> Result<(), String> {
    fs::write(&path, content).map_err(|e| format!("Failed to write {path}: {e}"))
}

#[command]
fn list_dir(path: String) -> Result<Vec<String>, String> {
    let entries = fs::read_dir(&path).map_err(|e| format!("Failed to read dir {path}: {e}"))?;
    let names = entries
        .filter_map(|e| e.ok())
        .map(|e| e.file_name().to_string_lossy().into_owned())
        .collect();
    Ok(names)
}

// Spawns the FastAPI backend process. Only called in release builds; in dev mode the user
// runs `make dev` separately (or `make run` to start both in one terminal).
fn spawn_backend() -> Option<Child> {
    std::process::Command::new("sh")
        .arg("-c")
        .arg("uv run uvicorn vibe_ide.main:app --host 0.0.0.0 --port 8000 --env-file ../.env")
        .current_dir(BACKEND_DIR)
        .spawn()
        .ok()
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
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_shell::init())
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
        .invoke_handler(tauri::generate_handler![read_file, write_file, list_dir])
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
