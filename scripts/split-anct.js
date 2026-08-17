const fs = require('fs');

const oid = '22779536eea35367b16fdd3c0ec83369ce2dec41b3e14e060df3f07084f9f9eb';
const src = `.git/lfs/objects/${oid.substring(0, 2)}/${oid.substring(2, 4)}/${oid}`;
const text = fs.readFileSync(src, 'utf8');

const start = text.indexOf('[');
const end = text.lastIndexOf('];');
if (start < 0 || end < 0) throw new Error('Structure inattendue');
const body = text.slice(start + 1, end);

const target = Math.floor(body.length / 2);
let pos = body.indexOf('},{"id":', target);
if (pos < 0) pos = body.lastIndexOf('},{"id":', target);
if (pos < 0) throw new Error('Aucune frontière trouvée');
pos += 1;

const part1 = 'var ANCT_POLITIQUE_VILLE = [\n' + body.slice(0, pos) + '\n];\n';
const part2 = 'var ANCT_POLITIQUE_VILLE_2 = [\n' + body.slice(pos) + '\n];\n' +
    '__registerDataSource("anct-politique-ville", ANCT_POLITIQUE_VILLE.concat(ANCT_POLITIQUE_VILLE_2));\n';

fs.writeFileSync('data/sources/anct-politique-ville.js', part1, 'utf8');
fs.writeFileSync('data/sources/anct-politique-ville-2.js', part2, 'utf8');

const count = (s) => (s.match(/\{"id":"/g) || []).length;
console.log('part1:', (part1.length / 1048576).toFixed(1), 'MB,', count(part1), 'elements');
console.log('part2:', (part2.length / 1048576).toFixed(1), 'MB,', count(part2), 'elements');
console.log('total:', count(part1) + count(part2));