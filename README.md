# Count CSV records and split into a new folder

Save three source files in a NEW empty lesson folder.

    python make_sample.py
    python bigcsv.py sample/sales.csv
    python bigcsv.py sample/sales.csv --split 500000 sample/sales-parts
    python -m unittest -v

Two Windows and two Ubuntu full replays run exact visible source versions. Final 43 small fixture tests pass (Unix pipe skips on Windows); symlink creation can skip where unavailable. Displayed stdout is first Windows output, not normalized or mixed. Pair differences are unittest time.
Only link/error changes: refuse input/ancestor symbolic links/reparse points, hardlinks, special files and traversal before CSV reads, including part verification. Output ancestors are checked before creating a NEW split folder. Read/metadata/split errors remain exit 1; usage and invalid split-size errors stay exit 2. Setup refuses linked parents/traversal and existing sample paths, without reset/deletion.
Original strict UTF-8/BOM CSV parsing, header/row checks, record counting, split sizes, CSV serialization, ordered parsed-field digest/count verification and printed relative filenames remain unchanged. Outputs are still exclusive new files in a NEW folder. No byte-preservation, Excel import or formula-safety promise was added. Parsed field values/order are verified, not raw quoting/bytes.
CSV is streamed, but no size/time/resource limit, atomic snapshot or hostile-race defense is provided. Stop editors/sync. Count output includes private paths; split parts contain source data. A split/write/verification failure can leave partial NEW parts; they are not deleted. Keep the source and inspect incomplete outputs; do not use them. Small fictional fixtures are not proof on every filesystem. No Excel/desktop Windows/macOS recording. Recorder removes only its own temporary fixture folder. Decisions/feedback are teaching text, not recorded output.

MIT code. Python separately licensed/not included.

Reference: https://docs.python.org/3/library/os.html
Windows paired run: https://github.com/faiz12321/lesson-lab/actions/runs/38978182023
Ubuntu paired run: https://github.com/faiz12321/lesson-lab/actions/runs/38978370213
