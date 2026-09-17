<!-- file-edit-size-limits:start -->
## Chunked Assembly for Large File Operations

Keep each tool call within output limits to avoid token truncation, broken JSON payloads, and tool failure:

- **300-line ceiling:** generate or replace at most **300 lines of content** per `write` or `edit` call.
- **Chunk large files in steps:** for a file expected to exceed 300 lines, assemble it incrementally:
  1. **Initialize:** use `write` to lay down the file outline, high-level structure, exports, or boilerplate.
  2. **Populate:** add distinct sections, blocks, or content groups with sequential `edit` calls.
<!-- file-edit-size-limits:stop -->