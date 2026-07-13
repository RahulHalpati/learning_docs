# 02 · Building the nodes

Now you build the pipeline one node at a time. Each module takes a single node
from the capstone's [`faceless_studio/`](../99_project_faceless_studio/faceless_studio/)
package, explains it, and hands you an exercise.

| # | Module | Node | Type |
|---|---|---|---|
| 02-1 | [Shared state](01_shared_state.md) | `VideoState` | data |
| 02-2 | [Researcher](02_researcher.md) | `topic_researcher` | LLM |
| 02-3 | [Scriptwriter](03_scriptwriter.md) | `script_writer` | LLM + parsing |
| 02-4 | [Voiceover](04_voiceover.md) | `voiceover` | media (TTS) |
| 02-5 | [Visuals](05_visuals.md) | `visuals` | media (Pillow) |
| 02-6 | [Assembler](06_assembler.md) | `assembler` | media (ffmpeg) |
| 02-7 | [Metadata & SEO](07_metadata.md) | `metadata` | LLM + logic |

Build them in order — later nodes consume what earlier ones produce.

**Next → [02-1 · Shared state](01_shared_state.md)**
