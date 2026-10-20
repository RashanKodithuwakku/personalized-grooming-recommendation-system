# Component 3 training notebook — viva / evidence guide

**Notebook (preserved byte-for-byte; do not rewrite outputs):**  
`backend/training/notebooks/Component3_Training_Executed.ipynb`

| Property | Value |
|----------|-------|
| SHA256 (as of evidence refresh) | `8362adf763c69182cdfadcc20dd3b6a187c549b2476716328a60db018b5baad8` |
| Size | 13 780 006 bytes |
| Total entries in `cells` array | 101 (indices **0–100**) |

## Cell numbering (important)

The audit phrase **“cells 95–97”** refers to **0-based indices** in the notebook JSON `cells` list (`nb['cells'][95]` … `[97]`).

| 0-based index (audit wording) | 1-based position if counting from the top as cell 1 | Role |
|-------------------------------|-----------------------------------------------------|------|
| 94 | 95 | Gender-aware schema / feature contract preparation |
| **95** | **96** | **Final GenderAware training + model export** |
| **96** | **97** | **Final evaluation tables (match exported CSVs)** |
| **97** | **98** | **Download of final run zip** (`…20261008T123658_164628Z`) |

This README uses **0-based indices** unless marked “1-based”.

**All `execution_count` fields are `null`.** Execution order **cannot** be reconstructed from those fields. Do not invent execution counts or claim a continuous Colab “Run all” certificate solely from the filename.

## Final successful GenderAware path (use these in viva)

### Index 95 — training and export

- Creates run folder under Colab Drive: `Component3_GenderAware_<stamp>/`
- Trains three `CatBoostRanker` models (hair, beard, grooming) and one `CatBoostRegressor` (compatibility)
- Writes `.cbm` files, hashes, schema, run metadata
- Aligns with on-disk artifacts under `backend/models/` and nested `backend/models/models/`
- `run_information.json` records run folder  
  `…/Component3_GenderAware_20261008T123658_164628Z`

### Index 96 — evaluation

- Computes ranker **top-choice agreement** and **NDCG@3**, plus scorer **MAE** / **RMSE**
- Saved notebook **outputs** show tables that match current:
  - `backend/models/gender_evaluation.csv`
  - `backend/models/gender_scorer_errors.csv`
- These metrics measure agreement with **rule-generated** ratings, not human suitability

### Index 97 — artifact download

- Downloads  
  `Component3_GenderAware_20261008T123658_164628Z.zip`  
  which is the same run id as `backend/models/run_information.json`

## Earlier experimental / historical cells (not the final shipped run)

The notebook is a **composite Colab history**, not a single clean linear pipeline.

| Region (approx. 0-based) | Content | Relation to final models |
|--------------------------|---------|---------------------------|
| Early cells | Imports, data unpacking, exploratory prep | Supporting / historical |
| ~35–88 | Earlier CatBoost ranker/scorer experiments, baselines, metrics | **Superseded** by GenderAware cells 95–96 |
| ~57 | CLIP / IndicFairFace auto-label attempt | **Fails** with `AttributeError: 'BaseModelOutputWithPooling' object has no attribute 'norm'` |
| ~59–69 | Image-folder / auto-label diagnostics | Experimental; not used by the FastAPI runtime |
| ~93–94 | Gender column / schema prep for GenderAware | Prep for final run |
| 95–97 | Final GenderAware train / eval / download | **Authoritative for shipped binaries** |
| 98–100 | Metadata / additional download helpers | Ancillary |

### Does the CLIP error invalidate the final models?

**No.** Cell **57** is an earlier experimental auto-labeling path. The shipped gender-aware CatBoost binaries and evaluation CSVs correspond to the **later GenderAware training/evaluation cells (95–96)** and the zip named in cell **97** / `run_information.json`. The CLIP failure does **not** rewrite those `.cbm` files.

## What this README does *not* claim

- That every cell from top to bottom runs successfully today  
- That `execution_count` proves order  
- That notebook outputs were regenerated in this documentation pass  
- That metrics are human suitability accuracy or calibrated recommendation confidence  

No training rerun was performed for this documentation task.
