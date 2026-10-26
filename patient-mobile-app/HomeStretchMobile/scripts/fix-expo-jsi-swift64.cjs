// ExpoModulesJSI 57.1.1 only strips the pre-Swift-6.4 C++ namespace spelling.
const fs = require('node:fs');
const path = require('node:path');
const root = path.dirname(require.resolve('expo-modules-jsi/package.json'));
const script = path.join(root, 'apple/scripts/build-xcframework.sh');
const source = fs.readFileSync(script, 'utf8');
const oldRule = String.raw`/^extension __ObjC\./`;
const newRule = String.raw`/^extension __ObjC[.:]/`;
if (source.includes(oldRule)) {
  fs.writeFileSync(script, source.replace(oldRule, newRule));
} else if (!source.includes(newRule)) {
  throw new Error('ExpoModulesJSI cleanup changed; review the Swift 6.4 workaround.');
}
