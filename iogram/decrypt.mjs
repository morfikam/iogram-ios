// Расшифровка Iogram.ipa.enc (артефакт сборки) — формат `openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -md sha256`.
// node iogram/decrypt.mjs <Iogram.ipa.enc> <Iogram.ipa> <файл с паролем>
import crypto from 'node:crypto';
import fs from 'node:fs';

const ITERATIONS = 200000;
const [input, output, keyFile] = process.argv.slice(2);
if (!input || !output || !keyFile) {
  console.error('node decrypt.mjs <Iogram.ipa.enc> <Iogram.ipa> <файл с паролем>');
  process.exit(1);
}

const data = fs.readFileSync(input);
if (data.subarray(0, 8).toString('latin1') !== 'Salted__') throw new Error('Это не файл openssl enc');
const salt = data.subarray(8, 16);
const password = fs.readFileSync(keyFile, 'utf8').trim();
const derived = crypto.pbkdf2Sync(password, salt, ITERATIONS, 48, 'sha256');
const decipher = crypto.createDecipheriv('aes-256-cbc', derived.subarray(0, 32), derived.subarray(32));
fs.writeFileSync(output, Buffer.concat([decipher.update(data.subarray(16)), decipher.final()]));
console.log('Расшифровано:', output);
