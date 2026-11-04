import ast
import base64
import io
import json
from pathlib import Path
import tempfile
import zipfile
import py_compile

def verify_notebook(nb_path: Path):
    print("=" * 70)
    print(f"VERIFYING NOTEBOOK: {nb_path.name}")
    print("=" * 70)
    
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)
        
    print(f"  Total cells: {len(nb['cells'])}")
    
    # 1. AST compilation check for all code cells
    for idx, cell in enumerate(nb["cells"]):
        if cell["cell_type"] == "code":
            code = "".join(cell["source"])
            # Strip IPython magic commands like %cd, !pip for pure AST check
            clean_lines = []
            for line in code.splitlines():
                stripped = line.strip()
                if stripped.startswith("%") or stripped.startswith("!"):
                    clean_lines.append("# " + line)
                else:
                    clean_lines.append(line)
            clean_code = "\n".join(clean_lines)
            try:
                ast.parse(clean_code)
            except SyntaxError as e:
                print(f"  [ERROR] Syntax error in cell {idx}: {e}")
                raise e
    print("  [OK] All code cells passed AST parse verification.")
    
    # 2. Extract and test EMBEDDED_CODE_B64 from Cell 6
    cell6 = nb["cells"][6]
    cell6_src = "".join(cell6["source"])
    
    # Find EMBEDDED_CODE_B64 definition
    scope = {}
    lines = []
    in_b64 = False
    for l in cell6["source"]:
        if "EMBEDDED_CODE_B64 = (" in l:
            in_b64 = True
            lines.append(l)
        elif in_b64:
            lines.append(l)
            if l.strip() == ")":
                in_b64 = False
                break
    
    b64_code = "".join(lines)
    exec(b64_code, scope)
    b64_str = scope["EMBEDDED_CODE_B64"]
    raw_zip = base64.b64decode(b64_str)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with zipfile.ZipFile(io.BytesIO(raw_zip), "r") as zf:
            zf.extractall(tmp_path)
            
        train_py = tmp_path / "ml" / "segmentation" / "train_seg.py"
        assert train_py.exists(), f"train_seg.py not found in unpacked zip: {list(tmp_path.rglob('*'))}"
        
        train_content = train_py.read_text(encoding="utf-8")
        
        # Verify .reshape is present and .view is absent in tensor flattening
        assert "p = preds.reshape(preds.size(0), -1)" in train_content, "compute_batch_dice_iou does not use .reshape for preds!"
        assert "t = targets.reshape(targets.size(0), -1)" in train_content, "compute_batch_dice_iou does not use .reshape for targets!"
        assert "p = probs.reshape(probs.size(0), -1)" in train_content, "CombinedBCEDiceLoss does not use .reshape for probs!"
        assert "t = targets.reshape(targets.size(0), -1)" in train_content, "CombinedBCEDiceLoss does not use .reshape for targets!"
        assert "p_crop = probs[i : i + 1, :, :oh, :ow].contiguous()" in train_content, "p_crop is not contiguous!"
        assert "m_crop = masks[i : i + 1, :, :oh, :ow].contiguous()" in train_content, "m_crop is not contiguous!"
        assert "batch_size=1," in train_content, "val_loader batch_size is not 1!"
        
        py_compile.compile(str(train_py), doraise=True)
        print("  [OK] Embedded train_seg.py unpacked and verified (contains .reshape, .contiguous, batch_size=1).")
        
        # Verify evaluate_seg.py compiles
        eval_py = tmp_path / "ml" / "segmentation" / "evaluate_seg.py"
        assert eval_py.exists(), "evaluate_seg.py not found in unpacked zip!"
        py_compile.compile(str(eval_py), doraise=True)
        print("  [OK] Embedded evaluate_seg.py unpacked and compiled cleanly.")

    print(f"  [SUCCESS] {nb_path.name} is 100% verified!\n")

if __name__ == "__main__":
    verify_notebook(Path("infrascan/ml/notebooks/09_train_seg_kaggle.ipynb"))
    verify_notebook(Path("infrascan/ml/notebooks/10_eval_seg_kaggle.ipynb"))

