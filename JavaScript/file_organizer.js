const fs = require('fs');
const path = require('path');
const yargs = require('yargs/yargs');
const { hideBin } = require('yargs/helpers');

const argv = yargs(hideBin(process.argv))
  .option('help', {
    alias: 'h',
    type: 'boolean',
    description: 'ヘルプメッセージを表示して終了します'
  })
  .option('dir', {
    type: 'string',
    description: '処理対象となるディレクトリを指定します',
    demandOption: true
  })
  .option('extensions', {
    type: 'array',
    description: '処理対象となるファイルを拡張子で指定します'
  })
  .option('file_name', {
    type: 'array',
    description: '処理対象となるファイルをファイル名で指定します'
  })
  .option('save', {
    type: 'string',
    description: '処理対象として設定されたファイルを、このディレクトリに保存します'
  })
  .option('keep_structure', {
    type: 'boolean',
    description: '指定されたディレクトリの構造を保持します'
  })
  .option('debug', {
    type: 'boolean',
    description: 'デバッグ用に処理情報を表示します。実際には処理を実行しません'
  })
  .option('copy', {
    type: 'boolean',
    description: 'ファイルをコピーします'
  })
  .option('cut', {
    type: 'boolean',
    description: 'ファイルを移動します'
  })
  .check((argv) => {
    if (!argv.copy && !argv.cut) {
      throw new Error('`--copy`か`--cut`のどちらかを指定する必要があります');
    }
    return true;
  })
  .help()
  .argv;

if (argv.help) {
  yargs.showHelp();
  process.exit(0);
}

const processFiles = (sourceDir, targetDir, extensions, fileNames, keepStructure, debug, copy) => {
  const filesToProcess = [];

  const walkDir = (dir) => {
    const files = fs.readdirSync(dir);
    files.forEach((file) => {
      const fullPath = path.join(dir, file);
      const stat = fs.statSync(fullPath);

      if (stat.isDirectory()) {
        walkDir(fullPath);
      } else {
        if ((!extensions || extensions.includes(path.extname(file))) &&
            (!fileNames || fileNames.includes(file))) {
          filesToProcess.push(fullPath);
        }
      }
    });
  };

  walkDir(sourceDir);

  filesToProcess.forEach((file) => {
    const relativePath = path.relative(sourceDir, file);
    const targetPath = keepStructure ? path.join(targetDir, relativePath) : path.join(targetDir, path.basename(file));
    const targetDirPath = path.dirname(targetPath);

    if (debug) {
      console.log(`${copy ? 'Copy' : 'Move'}: ${file} -> ${targetPath}`);
    } else {
      if (!fs.existsSync(targetDirPath)) {
        fs.mkdirSync(targetDirPath, { recursive: true });
      }
      if (copy) {
        fs.copyFileSync(file, targetPath);
      } else {
        fs.renameSync(file, targetPath);
      }
    }
  });
};

processFiles(argv.dir, argv.save, argv.extensions, argv.file_name, argv.keep_structure, argv.debug, argv.copy);
