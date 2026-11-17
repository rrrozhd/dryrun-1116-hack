"""Download public weights explicitly, then generate locally without credentials."""

import argparse
import json
import os
from pathlib import Path
import platform
import time

# Never send an ambient Hugging Face login token when downloading public files.
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"

from huggingface_hub import snapshot_download

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
CACHE = Path(__file__).resolve().parent / ".models"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Download pinned weights only; no inference")
    parser.add_argument("--prompt", default="In one sentence, explain why ambiguous CSV values should remain unchanged.")
    args = parser.parse_args()

    # Without --download this call and both model loads use only local files.
    snapshot = snapshot_download(
        repo_id=MODEL,
        revision=REVISION,
        cache_dir=CACHE,
        token=False,
        local_files_only=not args.download,
        allow_patterns=["*.json", "*.safetensors", "*.txt", "LICENSE", "README.md"],
    )
    if args.download:
        print(json.dumps({"model": MODEL, "revision": REVISION, "downloaded": True}))
        return

    import torch
    import transformers
    from transformers.models.auto.modeling_auto import AutoModelForCausalLM
    from transformers.models.auto.tokenization_auto import AutoTokenizer

    started = time.monotonic()
    tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True, token=False, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(
        snapshot, local_files_only=True, token=False, trust_remote_code=False,
        use_safetensors=True, torch_dtype=torch.float32,
    ).to("cpu").eval()
    messages = [{"role": "user", "content": args.prompt}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt")
    with torch.inference_mode():
        output = model.generate(**inputs, max_new_tokens=64, do_sample=False)
    generated = output[0][inputs["input_ids"].shape[1]:]
    response = tokenizer.decode(generated, skip_special_tokens=True)
    if not response.strip():
        raise RuntimeError("The local model generated no text.")
    print(json.dumps({
        "model": MODEL, "revision": REVISION, "python": platform.python_version(),
        "torch": torch.__version__, "transformers": transformers.__version__,
        "device": "cpu", "dtype": "float32", "do_sample": False, "max_new_tokens": 64,
        "prompt": args.prompt, "response": response, "generated_tokens": len(generated),
        "load_and_generate_seconds": round(time.monotonic() - started, 3),
    }, indent=2))


if __name__ == "__main__":
    main()
