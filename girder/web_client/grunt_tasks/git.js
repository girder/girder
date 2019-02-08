const { execSync } = require('child_process');

// Third-party packages like 'git-revision-webpack-plugin' do not fail gracefully when not in a Git
// repo. This uses the exact same command as 'git-revision-webpack-plugin', but with better error
// handling.
function getGitSha() {
    try {
        return execSync(
            'git rev-parse HEAD',
            {
                stdio: [
                    'ignore', // stdin
                    'pipe', // stdout
                    // Suppress stderr from the command
                    'ignore' // stderr
                ]
            }
        )
            .toString() // the output could be a Buffer
            .trim();
    } catch (e) {
        // Gracefully fail if Git isn't available or this isn't a repo
        return null;
    }
}

module.exports = {
    getGitSha
};
