## Mermaid 対応 kind と最小サンプル

diagramブロックのMermaid sourceは、mermaid.js v11系が対応する記法から選ぶ。同梱済み `mermaid.min.js` がHTML上でSVGに置換する。

主要 kind:

| kind | 用途 |
|---|---|
| `flowchart` / `graph` | 処理・依存関係のフロー |
| `sequenceDiagram` | 相互作用・時系列メッセージ |
| `stateDiagram-v2` | 状態遷移 |
| `classDiagram` | クラス構造・継承・関連 |
| `erDiagram` | エンティティ関係 |
| `gantt` | 期間・スケジュール |
| `journey` | ユーザー体験の順序 |
| `timeline` | 時系列イベント |
| `mindmap` | 概念マップ・分類 |
| `pie` | 割合 |
| `gitGraph` | ブランチ・マージ |
| `requirementDiagram` | 要件・トレーサビリティ |
| `quadrantChart` | 2軸マトリクス |
| `sankey` | フロー量 |
| `xychart-beta` | 2次元数値プロット |
| `architecture-beta` | システム構成 |
| `block-beta` | ブロック配置 |
| `packet-beta` | パケット構造 |
| `kanban` | カンバンボード |
| `radar` | レーダーチャート |
| `treemap` | 階層構造の面積表現 |
| `zenuml` | ZenUML記法 |

最小サンプル:

`erDiagram`

    erDiagram
        CUSTOMER ||--o{ ORDER : places
        CUSTOMER {
            string id PK
            string name
        }
        ORDER {
            string id PK
            string customer_id FK
        }

`sequenceDiagram`

    sequenceDiagram
        participant User
        participant API
        User->>API: request
        API-->>User: response

`stateDiagram-v2`

    stateDiagram-v2
        [*] --> Idle
        Idle --> Running: start
        Running --> Idle: stop

`flowchart LR`

    flowchart LR
        A[Input] --> B{Decide}
        B -->|yes| C[Do it]
        B -->|no| D[Skip]

sourceの記法が不確かな場合は mermaid.js 公式docs (https://mermaid.js.org/) を参照する。schemaの `diagram_kind` は表示ラベル用のグループ名で、Mermaidの内部kind名と一致させる必要はない。
