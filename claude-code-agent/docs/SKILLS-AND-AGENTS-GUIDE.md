# Skills & Agents Upload Guide

## Overview

Yes! The dashboard has **full upload capabilities** for skills and agents. All uploaded files are **automatically persisted** to the `/data` volume, so they survive container restarts.

---

## 📦 How to Upload Skills via Dashboard

### **Method 1: Using the Dashboard UI** (Easiest)

1. **Open the Dashboard**
   - Navigate to http://localhost:8000

2. **Click the Registry Button**
   - Top right: Click **📦 Registry**

3. **Go to Skills Tab**
   - Click **Skills** tab in the modal

4. **Click Upload Skill**
   - Click **+ Upload Skill** button

5. **Fill the Form**
   - **Skill Name:** Enter folder name (e.g., `my-custom-skill`)
   - **Files:** Select all files for your skill
     - **REQUIRED:** `SKILL.md` (skill description)
     - **OPTIONAL:** `scripts/run.py`, `scripts/setup.sh`, etc.

6. **Submit**
   - Click **Upload Skill**
   - Files are saved to `/data/config/skills/my-custom-skill/`

### **Method 2: Using the API** (Programmatic)

```bash
# Upload a skill with multiple files
curl -X POST http://localhost:8000/api/registry/skills/upload \
  -F "name=my-skill" \
  -F "files=@SKILL.md" \
  -F "files=@scripts/run.py" \
  -F "files=@scripts/setup.sh"
```

---

## 🤖 How to Create Skills (Step-by-Step)

### **Example: Creating a Custom Skill**

#### **Step 1: Create Skill Files Locally**

Create a folder structure:
```
my-custom-skill/
├── SKILL.md           # Required: Skill description
└── scripts/
    └── run.py         # Optional: Helper scripts
```

#### **Step 2: Write SKILL.md**

```markdown
# My Custom Skill

This skill helps with custom data processing tasks.

## Usage

Use this skill when you need to:
- Process CSV files
- Generate reports
- Transform data

## Examples

Example 1: Process a CSV file
Example 2: Generate a summary report
```

#### **Step 3: Add Scripts (Optional)**

`scripts/run.py`:
```python
#!/usr/bin/env python3
"""Helper script for data processing."""

def process_data(input_file):
    # Your custom logic here
    pass

if __name__ == "__main__":
    import sys
    process_data(sys.argv[1])
```

#### **Step 4: Upload via Dashboard**

1. Open http://localhost:8000
2. Click **📦 Registry** → **Skills** tab
3. Click **+ Upload Skill**
4. Name: `my-custom-skill`
5. Select both `SKILL.md` and `scripts/run.py`
6. Click **Upload Skill**

**Done!** Your skill is now available at `/data/config/skills/my-custom-skill/`

---

## 🧠 How to Tell the Agent to Use Your Skill

### **Method 1: Via Chat (Easiest)**

In the dashboard chat:
```
Use the my-custom-skill to process the data.csv file
```

The Brain will automatically detect and use your uploaded skill.

### **Method 2: Via API**

```bash
curl -X POST http://localhost:8000/api/chat?session_id=my-session \
  -H "Content-Type: application/json" \
  -d '{
    "type": "chat.message",
    "message": "Use my-custom-skill to analyze the data"
  }'
```

---

## 🔧 How to Create Subagents

### **Subagent Structure**

Subagents are stored in folders with a `.claude` directory:

```
my-subagent/
└── .claude/
    └── CLAUDE.md      # Agent instructions
```

### **Example: Creating a Database Expert Subagent**

#### **Step 1: Create Agent Files**

`my-db-expert/.claude/CLAUDE.md`:
```markdown
# Database Expert Agent

You are a database expert specializing in SQL optimization and schema design.

## Your Role

- Analyze database schemas
- Optimize SQL queries
- Suggest indexing strategies
- Design efficient data models

## Tools Available

- Read: View database files
- Edit: Modify SQL files
- Bash: Run database commands

## Guidelines

1. Always explain your reasoning
2. Provide performance metrics
3. Suggest best practices
```

#### **Step 2: Upload via File System**

Since agents are more complex, you can upload them directly to the volume:

```bash
# Copy agent to the data volume
docker cp my-db-expert claude-code-agent:/data/config/agents/my-db-expert
```

Or create them programmatically via the API (future enhancement).

---

## 💾 File Persistence - Where Files Are Saved

### **Storage Locations**

All uploaded files are saved to the **persistent `/data` volume**:

| Type | Location | Persists? |
|------|----------|-----------|
| **User Skills** | `/data/config/skills/` | ✅ Yes |
| **User Agents** | `/data/config/agents/` | ✅ Yes |
| **Credentials** | `/data/credentials/claude.json` | ✅ Yes |
| **Database** | `/data/db/machine.db` | ✅ Yes |
| **Builtin Skills** | `/app/skills/` | ❌ No (read-only) |
| **Builtin Agents** | `/app/agents/` | ❌ No (read-only) |

### **Verify Persistence**

```bash
# Check uploaded skills
docker exec claude-code-agent ls -la /data/config/skills/

# Check uploaded agents
docker exec claude-code-agent ls -la /data/config/agents/

# Check credentials
docker exec claude-code-agent ls -la /data/credentials/
```

### **Volume Configuration**

In `docker-compose.yml`:
```yaml
volumes:
  - ./data:/data  # Persistent storage
```

This means:
- **Host:** `./data/` (on your machine)
- **Container:** `/data/` (inside Docker)
- **Survives:** Container restarts, rebuilds, updates

---

## 🎯 Complete Workflow Example

### **Scenario: Upload a Custom Skill and Use It**

#### **1. Create the Skill**

```bash
# Create skill folder
mkdir -p my-report-generator
cd my-report-generator

# Create SKILL.md
cat > SKILL.md << 'EOF'
# Report Generator Skill

Generates formatted reports from data files.

## Usage
Use this skill to create PDF/HTML reports from CSV or JSON data.
EOF

# Create helper script
mkdir scripts
cat > scripts/generate.py << 'EOF'
#!/usr/bin/env python3
import sys
print(f"Generating report from {sys.argv[1]}")
EOF
chmod +x scripts/generate.py
```

#### **2. Upload via Dashboard**

1. Open http://localhost:8000
2. Click **📦 Registry**
3. Click **Skills** tab
4. Click **+ Upload Skill**
5. Name: `my-report-generator`
6. Select `SKILL.md` and `scripts/generate.py`
7. Click **Upload Skill**

#### **3. Verify Upload**

```bash
# Check files were saved
docker exec claude-code-agent ls -la /data/config/skills/my-report-generator/
```

Output:
```
drwxr-xr-x  3 root root  96 Jan 22 11:52 .
drwxr-xr-x  3 root root  96 Jan 22 11:52 ..
-rw-r--r--  1 root root 123 Jan 22 11:52 SKILL.md
drwxr-xr-x  2 root root  64 Jan 22 11:52 scripts
```

#### **4. Use the Skill**

In the dashboard chat:
```
Use the my-report-generator skill to create a report from data.csv
```

The Brain will:
1. Detect your uploaded skill
2. Read the SKILL.md instructions
3. Execute the task using the skill's guidance

---

## 📋 Dashboard Features Available

### ✅ **What You Can Do via Dashboard**

| Feature | Available? | How to Access |
|---------|-----------|---------------|
| **Upload Skills** | ✅ Yes | Registry → Skills → Upload |
| **Delete Skills** | ✅ Yes | Registry → Skills → Delete button |
| **View Skills** | ✅ Yes | Registry → Skills tab |
| **View Agents** | ✅ Yes | Registry → Agents tab |
| **Upload Credentials** | ✅ Yes | Credentials button → Upload |
| **View Analytics** | ✅ Yes | Analytics tab |
| **View Tasks** | ✅ Yes | Tasks tab |
| **Chat with Brain** | ✅ Yes | Chat tab |

### ⚠️ **What's Not Yet Available**

| Feature | Status | Workaround |
|---------|--------|------------|
| **Upload Agents via UI** | Not yet | Use `docker cp` or mount volume |
| **Edit Skills in UI** | Not yet | Re-upload or edit via volume |

---

## 🔐 Credentials Upload

### **Upload Claude Credentials**

1. **Get your `claude.json`**
   - From `~/.claude/` on your machine

2. **Upload via Dashboard**
   - Click **🔑 Credentials**
   - Click **Choose File**
   - Select `claude.json`
   - Click **Upload**

3. **Verify**
   - Status should show "VALID"
   - Expiration date displayed

**File saved to:** `/data/credentials/claude.json`

---

## 🚀 Quick Start Checklist

- [ ] Dashboard running at http://localhost:8000
- [ ] Create skill folder with `SKILL.md`
- [ ] Upload skill via **📦 Registry** button
- [ ] Verify skill appears in skills list
- [ ] Test skill by chatting: "Use my-skill-name to..."
- [ ] Check `/data/config/skills/` for persistence

---

## 🛠️ Troubleshooting

### **Skill Upload Fails**

**Error:** "SKILL.md is required"
- **Solution:** Make sure you include `SKILL.md` in your file selection

**Error:** "Skill already exists"
- **Solution:** Delete the old skill first or use a different name

### **Files Not Persisting**

**Check volume mount:**
```bash
docker inspect claude-code-agent | grep -A 10 Mounts
```

Should show:
```json
"Mounts": [
    {
        "Type": "bind",
        "Source": "/path/to/your/data",
        "Destination": "/data"
    }
]
```

### **Can't See Uploaded Skill**

**Refresh the registry:**
- Close and reopen the Registry modal
- Or refresh the page

**Check file permissions:**
```bash
docker exec claude-code-agent ls -la /data/config/skills/
```

---

## 📚 Examples

### **Example 1: Data Analysis Skill**

`data-analyzer/SKILL.md`:
```markdown
# Data Analysis Skill

Analyzes CSV and JSON data files.

## Capabilities
- Statistical summaries
- Data visualization
- Trend detection
```

Upload and use:
```
Upload via dashboard → Use in chat: "Analyze sales.csv using data-analyzer skill"
```

### **Example 2: Code Review Skill**

`code-reviewer/SKILL.md`:
```markdown
# Code Review Skill

Reviews code for best practices and bugs.

## Focus Areas
- Security vulnerabilities
- Performance issues
- Code style
```

Upload and use:
```
Upload via dashboard → Use in chat: "Review app.py using code-reviewer skill"
```

---

## 🎓 Best Practices

1. **Always include SKILL.md** - Required for skill recognition
2. **Use descriptive names** - `data-analyzer` not `skill1`
3. **Document usage** - Clear examples in SKILL.md
4. **Test locally first** - Verify scripts work before uploading
5. **Version your skills** - Keep backups of skill folders
6. **Check persistence** - Verify files in `/data/config/skills/`

---

## Summary

**Yes, all these features are available and accessible via the dashboard:**

✅ Upload skills with multiple files  
✅ Files automatically saved to `/data` volume  
✅ Persist across container restarts  
✅ View all skills and agents  
✅ Delete user skills  
✅ Upload credentials  
✅ Full API access for automation  

**Access everything at:** http://localhost:8000
