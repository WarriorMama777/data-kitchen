use clap::{App, Arg};
use indicatif::{ProgressBar, ProgressStyle};
use std::fs;
use std::path::Path;
use std::thread;
use std::time::Duration;
use walkdir::WalkDir;

fn main() {
    let matches = App::new("File Organizer")
        .version("1.0")
        .author("Your Name")
        .about("Organizes files in a directory")
        .arg(Arg::new("dir")
            .long("dir")
            .takes_value(true)
            .help("Directory to process"))
        .arg(Arg::new("extensions")
            .long("extensions")
            .takes_value(true)
            .help("File extensions to process"))
        .arg(Arg::new("file_name")
            .long("file_name")
            .takes_value(true)
            .help("Specific file name to process"))
        .arg(Arg::new("save")
            .long("save")
            .takes_value(true)
            .help("Directory to save processed files"))
        .arg(Arg::new("preserve")
            .long("preserve")
            .takes_value(false)
            .help("Preserve the directory structure"))
        .arg(Arg::new("debug")
            .long("debug")
            .takes_value(false)
            .help("Run in debug mode without processing"))
        .arg(Arg::new("copy")
            .long("copy")
            .takes_value(false)
            .help("Copy files"))
        .arg(Arg::new("cut")
            .long("cut")
            .takes_value(false)
            .help("Move files"))
        .get_matches();

    let dir = matches.value_of("dir").unwrap_or(".");
    let save_dir = matches.value_of("save").unwrap_or(".");
    let preserve_structure = matches.is_present("preserve");
    let debug = matches.is_present("debug");
    let copy = matches.is_present("copy");
    let cut = matches.is_present("cut");

    if !copy && !cut {
        eprintln!("Either --copy or --cut must be specified.");
        std::process::exit(1);
    }

    if debug {
        println!("Running in debug mode...");
    }

    let entries: Vec<_> = WalkDir::new(dir).into_iter().filter_map(|e| e.ok()).collect();
    let pb = ProgressBar::new(entries.len() as u64);
    pb.set_style(
        ProgressStyle::default_bar()
            .template("{spinner:.green} [{elapsed_precise}] [{bar:40.cyan/blue}] {pos:>7}/{len:7} {msg}")
            .expect("Failed to set template") // ここで Result を処理します
            .progress_chars("#>-")
    );

    for entry in entries {
        let path = entry.path();
        let file_name = path.file_name().unwrap().to_str().unwrap();

        if let Some(extensions) = matches.value_of("extensions") {
            if !path.extension().map_or(false, |ext| extensions.contains(ext.to_str().unwrap())) {
                continue;
            }
        }

        if let Some(specific_file_name) = matches.value_of("file_name") {
            if file_name != specific_file_name {
                continue;
            }
        }

        if debug {
            println!("Processing: {}", path.display());
            continue;
        }

        let save_path = if preserve_structure {
            Path::new(save_dir).join(path.strip_prefix(dir).unwrap())
        } else {
            Path::new(save_dir).join(file_name)
        };

        // Retry loop with error handling
        let mut attempts = 0;
        while attempts < 3 {
            if let Some(parent) = save_path.parent() {
                if fs::create_dir_all(parent).is_err() {
                    eprintln!("Failed to create directory: {}", parent.display());
                    attempts += 1;
                    thread::sleep(Duration::from_secs(1));
                    continue;
                }
            }

            let result = if copy {
                fs::copy(path, &save_path).map(|_| ())
            } else if cut {
                fs::rename(path, &save_path)
            } else {
                break;
            };

            if result.is_err() {
                eprintln!("Failed to process file: {}", path.display());
                attempts += 1;
                thread::sleep(Duration::from_secs(1));
            } else {
                break;
            }
        }

        pb.inc(1);
    }

    pb.finish_with_message("Processing complete.");
}
