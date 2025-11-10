# Master Prompt (Condensed)

## 🚨 CRITICAL RULES - Every Session

1. **Verify before documenting:** Run `python verify_system_stats.py` before updating any stats
2. **Never delete macOS files:** Filter `._*` files, don't delete: `if not f.name.startswith('._')`
3. **Test claimed fixes:** Run the code/script - don't assume it works
4. **Read entry doc:** Check `CLAUDE_START_HERE.md` at start of every session
5. **Update docs immediately:** README + SESSION_NOTES after any changes

## 📁 Documentation Structure

**Start here:** `CLAUDE_START_HERE.md` - Critical rules & recurring issues
**Architecture:** `ARCHITECTURE.md` - System design & data flow
**Development:** `DEVELOPMENT.md` - Common tasks & workflow
**Troubleshooting:** `TROUBLESHOOTING.md` - Known issues & solutions
**History:** `CHANGELOG.md` - Completed items
**Planning:** `BACKLOG.md` - Future work

## 📊 Current System State (Nov 10, 2025)

**Verified stats:** Run `python verify_system_stats.py` for latest
- Books: 922 EPUB, 1,778 PGN games
- Chunks: 313,057 total (311,266 EPUB + 1,791 PGN)
- Diagrams: 536,243 extracted from books

**Infrastructure:**
- Flask: http://localhost:5001
- Qdrant: Docker, http://localhost:6333
- Git branch: phase-5.1-ui-integration
- External drive: /Volumes/T7 Shield/books/

## ⚡ Before Starting Any Work

```bash
# 1. Verify actual state
python verify_system_stats.py

# 2. Check git status
git status

# 3. Read relevant doc
# cat DEVELOPMENT.md  # for tasks
# cat TROUBLESHOOTING.md  # for bugs
# cat ARCHITECTURE.md  # for design questions
```

## 🐛 Recurring Issues (3-4 sessions)

**Problem:** Previous Claudes repeatedly:
1. Trusted docs instead of verifying → Stats were 40% inflated
2. Deleted macOS `._*` files → User had to rebuild them
3. Claimed "fixed" without testing → Bugs weren't actually fixed

**Solution:** Follow the 5 critical rules above + read CLAUDE_START_HERE.md

---

**Remember:** This prompt is a dashboard. For details, read the relevant .md file.
