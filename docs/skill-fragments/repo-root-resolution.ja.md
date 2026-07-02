CLI実行前に、この `SKILL.md` の配置から renderer repo root を決める。
`{{skill_path}}` の2階層上が renderer repo root であり、
そこに `scripts/html_review_workbench/cli.py` が存在することを確認する。
すべての `python3 -m scripts.html_review_workbench.cli ...` は renderer repo root を
作業ディレクトリにして実行する。現在のチャットやworkspaceのcwdをrepo rootとして扱わない。
cwdに `scripts/html_review_workbench/cli.py` が無い場合は、代替HTMLを作らず、
renderer repo rootへ移動してCLIを実行する。
