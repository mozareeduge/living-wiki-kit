# MAWS current state

**Thread:** `kit-finish-obsidian-20261014`  
**Status:** active  
**Objective:** Verify and repair the current release on Windows, finish an Obsidian interface using existing archive components, provide a verified walkthrough vault, and complete eligible release gates.  
**Active item:** walkthrough-release  
**Scope frozen:** True  
**Open subagent permits:** 0/1  
**Full verification runs:** 4/1  

## Work items

- `windows-release` [done] Prove and repair kit 1.4.0 on Windows — deps: -
- `obsidian-ui` [done] Finish native Obsidian workbench — deps: windows-release
- `walkthrough-release` [active] Install and verify walkthrough and release — deps: obsidian-ui

## Ready

none

## Summary

UI complete: bundled Field/Reader/Route/View/Review/Health works in native Obsidian, archive hashes unchanged. Core 1.4 released; PR10 carries UI. Next commit final packaging, obtain final CI and fresh-generator evidence, merge UI and deliver walkthrough package.
