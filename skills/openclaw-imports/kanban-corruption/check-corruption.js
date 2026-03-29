#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const KANBAN_FILE = '/root/.openclaw/workspace/kanban-tasks.json';
const ERRORS_FILE = '/root/.openclaw/workspace/tasks/taskerrors.md';

function getGitVersions(count = 3) {
  try {
    const log = execSync(`git log --oneline -${count + 5} -- kanban-tasks.json`, { cwd: '/root/.openclaw/workspace' })
      .toString()
      .split('\n')
      .filter(l => l.trim())
      .slice(0, count);
    
    const versions = [];
    for (const line of log) {
      const hash = line.split(' ')[0];
      try {
        const content = execSync(`git show ${hash}:kanban-tasks.json`, { cwd: '/root/.openclaw/workspace' }).toString();
        versions.push({ hash, data: JSON.parse(content) });
      } catch (e) {
        // Skip if can't read
      }
    }
    return versions;
  } catch (e) {
    console.log('Could not get git versions:', e.message);
    return [];
  }
}

function findMissingTasks(current, previous, listName) {
  const currentNames = new Set(current.map(t => t.name));
  const previousNames = previous.map(t => t.name);
  return previousNames.filter(name => !currentNames.has(name));
}

function loadErrors() {
  try {
    if (fs.existsSync(ERRORS_FILE)) {
      return fs.readFileSync(ERRORS_FILE, 'utf8');
    }
  } catch (e) {}
  return '# Kanban Task Errors\n\n';
}

function saveErrors(content) {
  const dir = path.dirname(ERRORS_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(ERRORS_FILE, content);
}

function main() {
  // Read current
  if (!fs.existsSync(KANBAN_FILE)) {
    console.log('No kanban file found');
    return;
  }
  
  const current = JSON.parse(fs.readFileSync(KANBAN_FILE, 'utf8'));
  const versions = getGitVersions(3);
  
  if (versions.length === 0) {
    console.log('No git versions to compare');
    return;
  }
  
  let allMissing = [];
  
  // Check each version
  for (const version of versions) {
    const prev = version.data;
    
    for (const listName of ['todo', 'in_progress', 'done', 'blocked']) {
      const missing = findMissingTasks(current[listName] || [], prev[listName] || [], listName);
      if (missing.length > 0) {
        for (const taskName of missing) {
          allMissing.push({
            task: taskName,
            fromList: listName,
            hash: version.hash
          });
        }
      }
    }
  }
  
  if (allMissing.length > 0) {
    console.log('Found missing tasks:', allMissing);
    
    // Deduplicate
    const unique = [];
    const seen = new Set();
    for (const m of allMissing) {
      const key = `${m.task}-${m.fromList}`;
      if (!seen.has(key)) {
        seen.add(key);
        unique.push(m);
      }
    }
    
    // Recover tasks
    for (const m of unique) {
      // Find task from git
      for (const v of versions) {
        const lists = [v.data.todo, v.data.in_progress, v.data.done, v.data.blocked];
        for (const list of lists) {
          const task = list?.find(t => t.name === m.task);
          if (task) {
            task.status = 'todo';
            task.notes = `[RECOVERED] Was in ${m.fromList} but lost - recovered from git ${m.hash}`;
            current.todo.push(task);
            console.log('Recovered:', m.task);
            break;
          }
        }
      }
    }
    
    // Save updated kanban
    fs.writeFileSync(KANBAN_FILE, JSON.stringify(current, null, 2));
    
    // Log to errors
    const now = new Date().toISOString();
    const errorLog = `
## ${now.split('T')[0]}
### ${now.split('T')[1].split('.')[0]} UTC
- **Type:** Lost tasks detected
- **Affected:** ${unique.map(u => `${u.task} (${u.fromList})`).join(', ')}
- **Recovered:** Yes
`;
    const errors = loadErrors() + errorLog;
    saveErrors(errors);
    console.log('Logged to taskerrors.md');
  } else {
    console.log('No missing tasks found');
  }
}

main();
