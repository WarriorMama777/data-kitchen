const fs = require('fs');
const path = require('path');
const os = require('os');

// コマンドライン引数の解析
const args = parseArgs(process.argv.slice(2));

// デバッグモードの設定
const isDebugMode = args['--debug'];

// 処理対象ディレクトリの設定
const targetDir = args['--dir'] || '.';

// 出力ディレクトリの設定
const outputDir = args['--save_dir'] || 'output';

// 処理対象の拡張子の設定
const targetExtensions = args['--extension'] ? args['--extension'].split(',') : ['txt'];

// 再帰的な処理の設定
const isRecursive = args['--recursive'];

// 先頭文字削除数の設定
const delFirstCount = parseInt(args['--del_first']) || 0;

// 末尾文字削除数の設定
const delLastCount = parseInt(args['--del_last']) || 0;

// 先頭に追加する文字列の設定
const addFirst = args['--add_first'] || '';

// 末尾に追加する文字列の設定
const addLast = args['--add_last'] || '';

// 先頭に連番を追加するかの設定
const addNumberFirst = args['--add_number_first'];

// 末尾に連番を追加するかの設定
const addNumberLast = args['--add_number_last'];

// 置換する文字列の設定
const replaceFrom = args['--replace'] ? args['--replace'].split(' ')[0] : '';
const replaceTo = args['--replace'] ? args['--replace'].split(' ')[1] : '';

// 指定した文字以降を削除するかの設定
const delAfter = args['--del_after'];

// 指定した文字以前を削除するかの設定
const delBefore = args['--del_before'];

// 指定した文字の後ろに文字を追加するかの設定
const addAfter = args['--add_after'] ? args['--add_after'].split(',')[0] : '';
const addAfterString = args['--add_after'] ? args['--add_after'].split(',')[1] : '';

// 指定した文字の前に文字を追加するかの設定
const addBefore = args['--add_before'] ? args['--add_before'].split(',')[0] : '';
const addBeforeString = args['--add_before'] ? args['--add_before'].split(',')[1] : '';

// 正規表現でマッチした箇所を削除するかの設定
const regDelPattern = args['--reg_del'] ? new RegExp(args['--reg_del']) : null;

// 正規表現でマッチした箇所以外を削除するかの設定
const regDelAroundPattern = args['--reg_del_around'] ? new RegExp(args['--reg_del_around']) : null;

// フォルダ名のみを対象とするかの設定
const isFolderOnly = args['--folder'];

// ファイル名のみを対象とするかの設定
const isFileOnly = args['--file'];

// メモリキャッシュの設定
const useMemCache = args['--mem_cache'] !== 'OFF';

// マルチスレッド処理の設定
const threadCount = parseInt(args['--threads']) || Math.max(1, os.cpus().length - 1);

// 処理対象のファイルパスを取得する
const targetFiles = getTargetFiles(targetDir, targetExtensions, isRecursive);

// ファイル名の変更処理
renameFiles(targetFiles, outputDir, useMemCache, threadCount);

/**
 * コマンドライン引数を解析する
 * @param {string[]} args コマンドライン引数
 * @returns {Object} 解析された引数
 */
function parseArgs(args) {
  const parsedArgs = {};
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg.startsWith('--')) {
      const key = arg;
      let value = true;
      if (args[i + 1] && !args[i + 1].startsWith('--')) {
        value = args[i + 1];
        i++;
      }
      parsedArgs[key] = value;
    }
  }
  return parsedArgs;
}

/**
 * 処理対象のファイルパスを取得する
 * @param {string} dir 処理対象ディレクトリ
 * @param {string[]} extensions 処理対象の拡張子
 * @param {boolean} isRecursive 再帰的な処理を行うか
 * @returns {string[]} 処理対象のファイルパス
 */
function getTargetFiles(dir, extensions, isRecursive) {
  const targetFiles = [];
  const files = fs.readdirSync(dir);
  for (const file of files) {
    const filePath = path.join(dir, file);
    const stats = fs.statSync(filePath);
    if (stats.isDirectory()) {
      if (isRecursive) {
        targetFiles.push(...getTargetFiles(filePath, extensions, isRecursive));
      }
    } else {
      const ext = path.extname(file).slice(1);
      if (extensions.includes(ext)) {
        targetFiles.push(filePath);
      }
    }
  }
  return targetFiles;
}

/**
 * ファイル名を変更する
 * @param {string} fileName ファイル名
 * @returns {string} 変更後のファイル名
 */
function renameFile(fileName) {
  let newFileName = path.basename(fileName, path.extname(fileName));
  const ext = path.extname(fileName);

  // 先頭文字削除
  if (delFirstCount > 0) {
    newFileName = newFileName.slice(delFirstCount);
  }

  // 末尾文字削除
  if (delLastCount > 0) {
    newFileName = newFileName.slice(0, -delLastCount);
  }

  // 先頭に文字列を追加
  if (addFirst) {
    newFileName = addFirst + newFileName;
  }

  // 末尾に文字列を追加
  if (addLast) {
    newFileName += addLast;
  }

  // 先頭に連番を追加
  if (addNumberFirst) {
    newFileName = `${fileCounter++}_${newFileName}`;
  }

  // 末尾に連番を追加
  if (addNumberLast) {
    newFileName += `_${fileCounter++}`;
  }

  // 文字列を置換
  if (replaceFrom) {
    newFileName = newFileName.replace(new RegExp(replaceFrom, 'g'), replaceTo);
  }

  // 指定した文字以降を削除
  if (delAfter) {
    newFileName = newFileName.split(delAfter)[0];
  }

  // 指定した文字以前を削除
  if (delBefore) {
    newFileName = newFileName.split(delBefore).pop();
  }

  // 指定した文字の後ろに文字列を追加
  if (addAfter) {
    newFileName = newFileName.replace(new RegExp(addAfter, 'g'), `$&${addAfterString}`);
  }

  // 指定した文字の前に文字列を追加
  if (addBefore) {
    newFileName = newFileName.replace(new RegExp(addBefore, 'g'), `${addBeforeString}$&`);
  }

  // 正規表現でマッチした箇所を削除
  if (regDelPattern) {
    newFileName = newFileName.replace(regDelPattern, '');
  }

  // 正規表現でマッチした箇所以外を削除
  if (regDelAroundPattern) {
    newFileName = newFileName.match(regDelAroundPattern)[0];
  }

  // フォルダ名のみを対象とする場合
  if (isFolderOnly) {
    return path.join(path.dirname(fileName), newFileName);
  }

  // ファイル名のみを対象とする場合
  if (isFileOnly) {
    return path.join(path.dirname(fileName), `${newFileName}${ext}`);
  }

  // デフォルト
  return path.join(path.dirname(fileName), `${newFileName}${ext}`);
}

/**
 * ファイル名を変更する (マルチスレッド対応)
 * @param {string[]} targetFiles 処理対象のファイルパス
 * @param {string} outputDir 出力ディレクトリ
 * @param {boolean} useMemCache メモリキャッシュを使用するか
 * @param {number} threadCount スレッド数
 */
function renameFiles(targetFiles, outputDir, useMemCache, threadCount) {
  const totalFiles = targetFiles.length;
  let processedFiles = 0;
  let fileCounter = 1;

  // 出力ディレクトリが存在しない場合は作成する
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  // メモリキャッシュを使用する場合
  if (useMemCache) {
    const memCache = {};

    // マルチスレッド処理
    const pool = new MemoryPool(threadCount);
    targetFiles.forEach((filePath) => {
      pool.run(() => {
        const newFilePath = renameFile(filePath);
        memCache[filePath] = newFilePath;
        processedFiles++;
        printProgress(processedFiles, totalFiles);
      });
    });
    pool.drain(() => {
      // メモリキャッシュから出力ディレクトリにファイルを書き込む
      for (const [oldPath, newPath] of Object.entries(memCache)) {
        const newDir = path.join(outputDir, path.relative(targetDir, path.dirname(newPath)));
        if (!fs.existsSync(newDir)) {
          fs.mkdirSync(newDir, { recursive: true });
        }
        const newFilePath = path.join(newDir, path.basename(newPath));
        fs.copyFileSync(oldPath, newFilePath);
      }
      console.log('処理が完了しました。');
    });
  } else {
    // メモリキャッシュを使用しない場合
    targetFiles.forEach((filePath) => {
      const newFilePath = renameFile(filePath);
      const newDir = path.join(outputDir, path.relative(targetDir, path.dirname(newFilePath)));
      if (!fs.existsSync(newDir)) {
        fs.mkdirSync(newDir, { recursive: true });
      }
      const newFullPath = path.join(newDir, path.basename(newFilePath));
      fs.copyFileSync(filePath, newFullPath);
      processedFiles++;
      printProgress(processedFiles, totalFiles);
    });
    console.log('処理が完了しました。');
  }
}

/**
 * 処理の進捗状況を表示する
 * @param {number} processed 処理済みのファイル数
 * @param {number} total 総ファイル数
 */
function printProgress(processed, total) {
  const progress = Math.floor((processed / total) * 100);
  const bar = '█'.repeat(Math.floor(progress / 5)) + '░'.repeat(20 - Math.floor(progress / 5));
  process.stdout.write(`\r[${bar}] ${progress}% (${processed}/${total})`);
  if (processed === total) {
    process.stdout.write('\n');
  }
}

/**
 * マルチスレッド処理用のプール
 */
class MemoryPool {
  constructor(threadCount) {
    this.threadCount = threadCount;
    this.queue = [];
    this.workers = [];
    this.createWorkers();
  }

  createWorkers() {
    for (let i = 0; i < this.threadCount; i++) {
      const worker = {
        thread: null,
        available: true,
      };
      this.workers.push(worker);
    }
  }

  run(task) {
    const availableWorker = this.workers.find((worker) => worker.available);
    if (availableWorker) {
      availableWorker.available = false;
      availableWorker.thread = new Promise((resolve) => {
        task();
        resolve();
      }).finally(() => {
        availableWorker.available = true;
        this.run(this.queue.shift());
      });
    } else {
      this.queue.push(task);
    }
  }

  drain(callback) {
    Promise.all(this.workers.map((worker) => worker.thread || Promise.resolve()))
      .then(callback)
      .catch((err) => console.error(err));
  }
}
