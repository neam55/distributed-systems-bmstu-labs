// Run the same acceptance commands locally and in GitHub Actions.
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const root = path.resolve(__dirname, '..');
const config = JSON.parse(fs.readFileSync(path.join(root, '.github/classroom/autograding.json'), 'utf8'));

for (const test of config.tests) {
  console.log(`Running: ${test.name}`);
  for (const command of [test.setup, test.run].filter(Boolean)) {
    const result = spawnSync(command, {
      cwd: root,
      shell: true,
      stdio: 'inherit',
      timeout: test.timeout * 60_000,
    });
    if (result.error || result.status !== 0) {
      if (result.error) console.error(result.error.message);
      process.exit(result.status || 1);
    }
  }
}
