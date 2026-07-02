# SKILL.md shared fragments

`docs/skill-fragments/*.md` is the managed source for shared sections in `skills/*/SKILL.md`.

Edit the fragment files, then run:

```bash
python3 scripts/build_skill_docs.py
python3 scripts/build_skill_docs.py --check
```

Do not edit text between `<!-- BEGIN SHARED: <name> -->` and `<!-- END SHARED: <name> -->` directly in `SKILL.md`. The generator overwrites those regions.

Each fragment must have both `<name>.ja.md` and `<name>.en.md`. Every `.ja.md` file must contain text.

An `.en.md` file may be an empty placeholder when the current `SKILL.md` section has no English counterpart. This preserves byte-for-byte stability of the generated skill text. If an English section is added to `SKILL.md` later, put that text in the matching `.en.md` file and the generator will include it automatically.

Keep Japanese and English text paired when both languages are present. Some fragments use target-specific placeholders because the surrounding skill names and examples differ while the generated `SKILL.md` text must stay stable.
