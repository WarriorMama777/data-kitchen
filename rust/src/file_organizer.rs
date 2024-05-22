use std::env;
use std::fs;
use std::path::{Path, PathBuf};

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        print_help();
        return;
    }

    let mut dir = PathBuf::new();
    let mut extensions = Vec::new();
    let mut file_names = Vec::new();
    let mut save_dir = PathBuf::new();
    let mut preserve_structure = false;
    let mut debug = false;
    let mut copy = false;
    let mut cut = false;

    for arg in &args[1..] {
        match arg.as_str() {
            "-h" | "--help" => {
                print_help();
                return;
            }
            "--dir" => {
                if let Some(dir_path) = args.get(args.iter().position(|x| x == arg).unwrap() + 1) {
                    dir = PathBuf::from(dir_path);
                } else {
                    eprintln!("Error: --dir requires a directory path");
                    return;
                }
            }
            "--extensions" => {
                if let Some(exts) = args.get(args.iter().position(|x| x == arg).unwrap() + 1) {
                    extensions = exts.split(',').map(|s| s.to_string()).collect();
                } else {
                    eprintln!("Error: --extensions requires a comma-separated list of extensions");
                    return;
                }
            }
            "--file_name" => {
                if let Some(names) = args.get(args.iter().position(|x| x == arg).unwrap() + 1) {
                    file_names = names.split(',').map(|s| s.to_string()).collect();
                } else {
                    eprintln!("Error: --file_name requires a comma-separated list of file names");
                    return;
                }
            }
            "--save" => {
                if let Some(save_path) = args.get(args.iter().position(|x| x == arg).unwrap() + 1) {
                    save_dir = PathBuf::from(save_path);
                } else {
                    eprintln!("Error: --save requires a directory path");
                    return;
                }
            }
            "--preserve-structure" => preserve_structure = true,
            "--debug" => debug = true,
            "--copy" => copy = true,
            "--cut" => cut = true,
            _ => {
                eprintln!("Error: Unknown argument '{}'", arg);
                return;
            }
        }
    }

    if !copy && !cut {
        eprintln!("Error: Either --copy or --cut is required");
        return;
    }

    if debug {
        println!("Directory: {:?}", dir);
        println!("Extensions: {:?}", extensions);
        println!("File names: {:?}", file_names);
        println!("Save directory: {:?}", save_dir);
        println!("Preserve structure: {}", preserve_structure);
        println!("Copy: {}", copy);
        println!("Cut: {}", cut);
    } else {
        organize_files(
            &dir,
            &extensions,
            &file_names,
            &save_dir,
            preserve_structure,
            copy,
            cut,
        );
    }
}

fn organize_files(
    dir: &Path,
    extensions: &[String],
    file_names: &[String],
    save_dir: &Path,
    preserve_structure: bool,
    copy: bool,
    cut: bool,
) {
    if !dir.is_dir() {
        eprintln!("Error: {:?} is not a directory", dir);
        return;
    }

    if !save_dir.is_dir() {
        eprintln!("Error: {:?} is not a directory", save_dir);
        return;
    }

    let mut files = Vec::new();

    if extensions.is_empty() && file_names.is_empty() {
        files = get_all_files(dir, preserve_structure);
    } else {
        for entry in fs::read_dir(dir).unwrap() {
            let entry = entry.unwrap();
            let path = entry.path();

            if path.is_dir() {
                files.append(&mut get_all_files(&path, preserve_structure));
            } else if extensions.contains(&path.extension().unwrap_or_default().to_string_lossy().to_string())
                || file_names.contains(&path.file_name().unwrap().to_string_lossy().to_string())
            {
                files.push(path);
            }
        }
    }

    for file in files {
        let dest_path = save_dir.join(file.file_name().unwrap());

        if copy {
            fs::copy(&file, &dest_path).unwrap();
        } else {
            fs::rename(&file, &dest_path).unwrap();
        }
    }
}

fn get_all_files(dir: &Path, preserve_structure: bool) -> Vec<PathBuf> {
    let mut files = Vec::new();

    for entry in fs::read_dir(dir).unwrap() {
        let entry = entry.unwrap();
        let path = entry.path();

        if path.is_dir() {
            files.append(&mut get_all_files(&path, preserve_structure));
        } else {
            if preserve_structure {
                files.push(path);
            } else {
                files.push(path.strip_prefix(dir).unwrap().to_path_buf());
            }
        }
    }

    files
}

fn print_help() {
    println!("Usage: organize_files [OPTIONS]");
    println!("Options:");
    println!("  -h, --help                   Print this help message");
    println!("  --dir <DIR>                  Directory to process (default: current directory)");
    println!("  --extensions <EXTENSIONS>    Comma-separated list of file extensions to process");
    println!("  --file_name <FILE_NAMES>     Comma-separated list of file names to process");
    println!("  --save <DIR>                 Directory to save processed files");
    println!("  --preserve-structure         Preserve directory structure when saving files");
    println!("  --debug                      Print debug information (no actual processing)");
    println!("  --copy                       Copy files instead of moving them");
    println!("  --cut                        Move files instead of copying them");
}
