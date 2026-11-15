# 321 AI Studio

## Dataset formats

- TXT / Markdown: plain text, one or more examples.
- JSONL: chat records with a messages array, or prompt/completion and instruction/output pairs.
- CSV: prompt/response, instruction/output, or input/completion columns.

For chat data, use examples that clearly separate user and assistant turns. A few kilobytes are enough only to test the pipeline; useful language behaviour requires a large, clean, varied dataset.

## Configuration

The GUI exposes training steps, width, transformer layers, attention heads, context length, batch size, learning rate, dropout, random seed, gradient accumulation and compute-device preference. The trainer validates parameter ranges and reports training and validation loss.

Device options:
- Auto: CUDA, then Apple MPS, then CPU.
- CPU: portable, usually slower.
- CUDA: requires a compatible NVIDIA GPU and CUDA-enabled PyTorch.
- MPS: requires supported Apple Silicon and PyTorch.

## Checkpoints and output

- checkpoints/latest.pt: resumable model + optimizer state.
- checkpoints/best.pt: best validation-loss model.
- model/model.pt: selected model for local inference.
- model/model_info.json: architecture, data and training metadata.
- status.json: project status.

Training can resume from a matching latest checkpoint. Checkpoints with a different architecture are not loaded.

## Important limitations

The current model is byte-level and trained from scratch. It has no pretrained knowledge, no retrieval system, no external knowledge source and no instruction-following guarantee. It is not equivalent to a pretrained foundation model. Model quality depends on dataset quality and scale, compute, tokenizer, architecture and training methodology. Loss values are diagnostics, not a direct measure of answer quality.

The trainer does not upload datasets or checkpoints. Keep private datasets and credentials out of training files. Do not place API keys in a dataset.
