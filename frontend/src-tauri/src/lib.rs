// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandEvent;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            let args: Vec<String> = std::env::args().collect();
            if args.contains(&"--no-sidecar".to_string()) {
                println!("Skipping sidecar startup as --no-sidecar was passed.");
                return Ok(());
            }

            if let Ok(sidecar_command) = app.shell().sidecar("server-sidecar") {
                if let Ok((mut rx, child)) = sidecar_command.spawn() {
                    tauri::async_runtime::spawn(async move {
                        let _child_handle = child;
                        while let Some(event) = rx.recv().await {
                            if let CommandEvent::Stdout(line) = event {
                                println!("sidecar: {}", String::from_utf8_lossy(&line));
                            } else if let CommandEvent::Stderr(line) = event {
                                println!("sidecar err: {}", String::from_utf8_lossy(&line));
                            }
                        }
                    });
                } else {
                    println!("Failed to spawn sidecar, continuing without it.");
                }
            } else {
                println!("Sidecar configuration not found, continuing without it.");
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![greet])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
