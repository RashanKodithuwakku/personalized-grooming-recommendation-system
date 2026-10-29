# Component 4 — AI-Assisted Hairstyle Recommendation and Preview System

## 1. Overview

Component 4 is the hairstyle recommendation and preview component of the **Personalized Grooming Recommendation System with AI Assistance** project. It provides a user-facing workflow for uploading a photograph, viewing a ranked hairstyle recommendation, generating a template-based preview, comparing the original and preview images, and giving feedback on the recommendation.

The component combines a Flutter frontend with a Python/FastAPI backend. The image-processing pipeline uses MediaPipe facial landmarks, a pretrained BiSeNet face-parsing model, OpenCV transformations and blending, NumPy-based feature-distance calculations, hairstyle template metadata, and SQLite persistence for user feedback. An optional HairFastGAN advanced-preview integration is also present in the backend/frontend code; its availability depends on a correctly configured and reachable HairFastGAN runtime/service.

> **Implementation note:** This README documents the implementation and prototype workflow reflected in the component code and development work. Some integrations use mock/ranked metadata or fixed reference data and should not be described as a fully trained end-to-end recommendation model. Advanced HairFastGAN preview generation depends on its external model/runtime being available.

---

## 2. Objectives

- Provide a simple interface for uploading a user's photograph.
- Identify facial landmarks and relevant hair regions from images.
- Compare hairstyle template attributes and choose a suitable variant within a selected style.
- Align a hairstyle template to the user's facial geometry.
- Generate a standard preview by processing and blending the template with the user's photograph.
- Display the original photograph and generated preview for comparison.
- Show a short explanation associated with the recommended style.
- Collect user feedback (`like` / `dislike`) and store it in SQLite.
- Offer another ranked style when the current recommendation is disliked.
- Provide an optional advanced-preview flow using HairFastGAN, when configured.
- Evaluate template alignment using fixed reference landmarks and Normalized Mean Error (NME) metrics.

## 3. Main Features

### 3.1 Photograph upload and preview workflow

The Flutter interface allows a user to select/upload an image and request a preview from the FastAPI backend. The frontend sends the image and relevant parameters, including gender and current recommendation rank. The backend processes the image and returns the preview path, before/after comparison path, explanation, and associated style information.

### 3.2 Facial landmark detection

MediaPipe Face Mesh is used to detect facial landmarks from the user's photograph. The implementation uses three anchor points:

1. Left-side jaw/face point (MediaPipe landmark 234).
2. Right-side jaw/face point (MediaPipe landmark 454).
3. Upper-face anchor (MediaPipe landmark 10).

Images are resized to a shared standard size of **512 × 512** before the relevant landmark and alignment calculations so that template coordinates and user coordinates use a consistent coordinate space. If no face is detected, preview generation returns an error rather than continuing with invalid landmarks.

### 3.3 Pretrained BiSeNet hair segmentation

PyTorch is used as the deep-learning framework for loading and running the pretrained BiSeNet face-parsing model. BiSeNet produces a pixel-level parsing output; the implementation extracts the hair class (class ID 17 in the current code) to create a binary hair mask.

The segmentation process includes:
- Reading the image and resizing it to the configured standard dimensions.
- Converting OpenCV's BGR image to RGB.
- Applying tensor conversion and ImageNet-style normalization.
- Running inference without gradient calculation (`torch.no_grad()`).
- Selecting the predicted class for each pixel.
- Extracting the hair pixels into a binary mask.
- Cleaning the mask using morphological operations and, in the refined implementation, retaining the largest connected component.
- Resizing the mask back to the source image dimensions when needed.

The user hair mask is used to measure approximate image geometry and to support the template fitting and original-hair removal/blending workflow. The template image is also segmented so that its hair region can be isolated. Results depend on the pretrained model, input-photo quality, lighting, pose, and the accuracy of the predicted hair mask.

**PyTorch and BiSeNet are different things:** PyTorch is the framework that loads and executes the network; BiSeNet is the segmentation architecture/model.

### 3.4 Hairstyle template library

The component stores hairstyle template metadata in a JSON library (for example, `templates/library.json`). Template records can contain information such as:
- Template/style identifier and gender.
- Image path.
- Three landmark coordinates used for alignment.
- Face-width ratio.
- Hair-density/occupancy score.

A helper script (`calculate_attributes.py` in the prototype code) calculates template attributes from annotated points and images:
- **Face-width ratio:** distance between the left and right jaw points, normalized by image width.
- **Hair-density score:** a texture/occupancy proxy calculated from a region above the forehead anchor in the earlier attribute-calculation implementation. In the later adaptive preview pipeline, user hair density is estimated from the proportion of foreground pixels inside the detected hair-mask bounding box.

These are simple image-derived features, not clinical or biological measurements of hair density.

### 3.5 Variant selection using NumPy

The selection module filters the JSON template library by style prefix and gender, then compares the user's feature vector with each candidate template's feature vector. The earlier selection function uses Euclidean distance between two values: face-width ratio and hair-density score. The candidate with the smallest distance is selected.

The more recent preview pipeline measures the user's face-width ratio and hair-mask occupancy from the uploaded photograph before selecting a variant. The implementation should be understood as a **feature-distance/template-matching approach**, not as a separately trained neural-network classifier. Some ranked recommendation data is provided through mock Component 3 data until the upstream recommendation component is connected to its final data source.

### 3.6 Ranked style recommendations

The prototype contains ranked style lists organized by gender and category. The available metadata includes style names, rank, and a confidence-like value. The current workflow selects a style by rank, then selects a matching template variant.

The codebase includes hairstyle and beard category structures in its mock ranked data. However, the current image preview pipeline explicitly reports that a beard preview needs a beard-specific segmentation/blending workflow and is **not implemented in the same way as hairstyle preview**. Do not present beard preview generation as fully implemented unless the backend has since been extended and tested.

### 3.7 Landmark alignment

OpenCV is used to align a template image to the user's facial anchor points:
- `cv2.getAffineTransform()` calculates a 2D affine transformation matrix from three corresponding points.
- `cv2.warpAffine()` transforms the template into the target coordinate space.
- The same transformation matrix can be applied to the template mask so the mask remains aligned with the warped template.

The later preview pipeline adds geometry-aware fitting steps around the isolated hair layer, including scaling/rotation and positioning relative to the user's landmarks and hair mask. These are deterministic image-processing operations; they are not themselves a trained AI model.

### 3.8 Original-hair removal, blending, and preview generation

The template-based preview pipeline includes the following processing stages, depending on the current backend revision:
1. Load and standardize the user photo and selected template.
2. Detect the user's facial landmarks.
3. Segment hair in the user photo and the template using BiSeNet.
4. Select a template variant from its metadata.
5. Align/fit the template hair to the user's face geometry.
6. Construct and refine a hair mask; the code saves intermediate masks for debugging.
7. Create a removal mask for the user's existing hair and use OpenCV inpainting to fill the masked area where supported by the current pipeline.
8. Place the fitted template-hair layer onto a canvas and blend it with the processed user photo.
9. Save the resulting standard preview.
10. Create a side-by-side original-versus-preview image.

The blending module uses mask-based alpha compositing and Gaussian smoothing of mask edges to reduce harsh boundaries. The standard preview is **template-based image manipulation**, not guaranteed photorealistic generative hairstyle transfer.

Intermediate outputs may include user/template hair masks, warped masks, combined/blend masks, hair-removal masks, cleaned user photos, standard previews, and before/after comparison images under the backend output/test-photo directory.

### 3.9 Before-and-after comparison

The comparison helper resizes the original and preview to a common height, preserves their aspect ratios, inserts a small white separator, and joins the images horizontally. The Flutter interface also displays the uploaded photo and recommended preview side by side in its “Before” and “After” area when the relevant UI version is used.

### 3.10 Explanation text

The explanation module generates a short text message using the selected style metadata and a set of contributing-factor values. The prototype example may return text such as “Recommended because of your jawline — 87% confidence match.”

**Important limitation:** In the current prototype, the contributing-factor values (for example, jawline, forehead, and symmetry) and confidence-like values can be mock/metadata values. This explanation is a rule-based template message, not a validated explanation from a trained explainable-AI model, and it should not be presented as a scientifically validated attractiveness score.

### 3.11 Feedback capture and ranked alternatives

The interface allows users to submit `like` or `dislike` feedback for the displayed style.

- A `dislike` response triggers the next ranked style in the same category when one is available.
- A `like` response can open a prompt asking whether the user wants an advanced preview.
- The backend validates the feedback value and saves the feedback record.
- A feedback-history endpoint can return saved records for inspection.

The current behavior is a simple next-rank workflow. Saving feedback does **not** automatically retrain BiSeNet or update the template-distance algorithm.

### 3.12 SQLite feedback database

`database.py` implements SQLite persistence. The database file is named `feedback.db`; the table is `feedback`. Stored fields include:
- Auto-incremented record ID.
- User ID.
- Style shown.
- Template variant shown.
- Feedback value (`like` or `dislike`).
- UTC timestamp.
- Style category/type.
- Current rank.

The database is initialized by the backend. `save_feedback()` accepts only `like` and `dislike` values and inserts a record using parameterized SQL. `get_all_feedback()` retrieves the stored records. SQLite is used for feedback persistence; the JSON template library is separate from the feedback database.

### 3.13 Fixed-reference alignment evaluation (NME)

The frontend includes an alignment evaluation section that requests metrics from the backend. The evaluation uses saved reference-user landmarks and template landmark data; the uploaded photo does not necessarily become the input to this fixed-reference calculation.

The evaluation compares:
- A fixed-overlay/resize baseline.
- An affine-aligned template.

The code reports Normalized Mean Error (NME) and error reduction where the reference inputs and evaluation implementation are available. The general calculation is:

`NME (%) = (mean landmark distance / normalizer) × 100`

`Error reduction (%) = ((baseline NME − affine NME) / baseline NME) × 100`

The normalizer in the current evaluation is based on the reference jaw-landmark distance. Lower NME indicates lower normalized landmark displacement. Metrics are only as meaningful as the selected reference points and annotation quality; they should not be described as universal model accuracy. The frontend labels the evaluation as fixed-reference because the calculation uses saved reference data.

### 3.14 Optional HairFastGAN advanced preview

The Flutter UI includes an advanced-preview choice and a request to the backend's `/advanced-preview` endpoint. The backend includes a HairFastGAN integration wrapper/status check and resolves a reference hairstyle image before attempting the advanced renderer. The intention is to use HairFastGAN for a more generative hairstyle-transfer result than the standard template-based preview.

This feature depends on the HairFastGAN repository, its pretrained weights and dependencies, and a reachable local or remote inference service. During development, the Colab attempt encountered `ModuleNotFoundError: No module named 'hair_swap'` because the repository files were not initially present in `/content`; the repository was subsequently cloned, but a successful complete preview from the Colab runtime has not been confirmed by the available conversation evidence. A previous API attempt also failed because the configured Cloudflare tunnel/API could not be reached. Therefore, document this as an **optional integration that requires runtime configuration and end-to-end verification**, not as guaranteed to work in every environment.

---

## 4. Technology Stack

| Technology | Role in Component 4 |
|---|---|
| Flutter / Dart | Frontend UI, photo upload, preview display, feedback controls, loading/error messages, alignment metrics display |
| Python | Backend logic and image-processing pipeline |
| FastAPI | REST API endpoints for preview generation, feedback, output images, alignment metrics, and optional advanced preview |
| PyTorch | Loads and runs the pretrained BiSeNet model |
| BiSeNet (pretrained) | Pixel-level face parsing used to extract the hair region |
| MediaPipe Face Mesh | Detects facial landmarks used as alignment anchors |
| OpenCV | Image loading/resizing, affine alignment, warping, morphology, inpainting, mask operations, blending, and image saving |
| NumPy | Feature vectors, Euclidean distance, mask calculations, and numerical metrics |
| JSON | Stores template library attributes and reference landmark data |
| SQLite | Persists user feedback records |
| Pillow (PIL) | Image conversion/handling and fallback image saving |
| HairFastGAN (optional) | Advanced generative hairstyle preview when its inference runtime is configured |

---

## 5. High-Level Architecture

```text
Flutter Frontend
    |
    | REST requests (HTTP)
    v
FastAPI Backend
    |
    +--> Preview pipeline
    |      +--> MediaPipe facial landmarks
    |      +--> PyTorch + BiSeNet hair segmentation
    |      +--> JSON template library and variant selection
    |      +--> OpenCV affine alignment / geometry-aware fitting
    |      +--> Hair mask refinement and original-hair inpainting
    |      +--> Mask-based blending
    |      +--> Preview and before/after image output
    |
    +--> Feedback service --> SQLite feedback.db
    |
    +--> Alignment evaluation --> fixed reference landmarks / NME
    |
    +--> Optional advanced preview --> HairFastGAN runtime/service
```

The frontend and backend communicate through API calls. The frontend is not expected to load BiSeNet or manipulate the SQLite database directly; those operations are performed by the Python backend.

---

## 6. Main API Endpoints

The exact available routes depend on the backend revision being run. The current updated backend includes the following routes:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Reports backend/model and HairFastGAN integration status |
| `GET` | `/styles` | Returns the available ranked styles for a gender and style category |
| `POST` | `/generate-preview` | Accepts a photo and generates the standard template-based preview |
| `GET` | `/outputs/{filename}` | Serves generated output images |
| `POST` | `/alignment-metrics` | Calculates fixed-reference alignment metrics |
| `POST` | `/feedback` | Saves a like/dislike and returns the next workflow action |
| `GET` | `/feedback` | Returns saved feedback history |
| `POST` | `/advanced-preview-choice` | Receives the user's choice about an advanced preview |
| `POST` | `/advanced-preview` | Attempts HairFastGAN preview generation if configured |

Useful development address when the backend runs locally: `http://127.0.0.1:8000`. FastAPI's interactive API documentation is usually available at `http://127.0.0.1:8000/docs`.

---

## 7. Project Structure

The names below describe the logical structure used by the implementation. Actual folder names may differ between the prototype ZIP and the latest working repository.

```text
project/
├── frontend/
│   └── lib/
│       └── main.dart                 # Flutter interface
└── backend/
    ├── main.py                       # FastAPI application and routes
    ├── main_flow.py                  # Preview and feedback orchestration
    ├── segmentation.py               # BiSeNet loading and hair-mask generation
    ├── landmarks.py                  # MediaPipe facial landmark detection
    ├── selection.py                  # Template variant selection
    ├── calculate_attributes.py       # Template feature calculation helper
    ├── alignment.py                  # Affine transformation and point utilities
    ├── blending.py                   # Mask-based alpha blending
    ├── comparison.py                 # Before/after image and preview metrics
    ├── explanation.py                 # Short recommendation explanation
    ├── mock_component3.py             # Prototype ranked style metadata
    ├── database.py                   # SQLite feedback persistence
    ├── alignment_evaluation.py       # Fixed-reference NME evaluation
    ├── hairfastgan.py                # Optional advanced-preview integration
    ├── config.py                     # Shared image dimensions/settings
    ├── templates/
    │   ├── library.json              # Template metadata and attributes
    │   ├── points_raw.json           # Annotated landmark coordinates (if used)
    │   ├── male/                     # Male hairstyle reference templates
    │   └── female/                   # Female hairstyle reference templates
    └── test_photos/                  # Inputs and generated diagnostic/output images
```

Some files, such as `alignment_evaluation.py` and `hairfastgan.py`, are part of the more recent integration and may not appear in older prototype bundles.

---

## 8. Setup and Running

### 8.1 Prerequisites

- Python 3.10 or a Python version compatible with the installed PyTorch, MediaPipe, and OpenCV packages.
- Flutter SDK and a supported device/emulator/desktop target for the frontend.
- The BiSeNet repository/module and its pretrained weight file.
- The template images and the matching JSON library/landmark coordinates.
- Optional: a working HairFastGAN environment, pretrained weights, and reachable inference service for advanced previews.

### 8.2 Python backend

Run commands from the backend directory that contains the FastAPI application. Create and activate a virtual environment, then install the project's pinned dependencies if a requirements file is supplied. If the repository has no complete requirements file, install compatible versions of the packages used by the code, including FastAPI, Uvicorn, `python-multipart`, Pydantic, PyTorch, torchvision, OpenCV, NumPy, MediaPipe, and Pillow.

Example setup:

```bash
cd backend
python -m venv .venv
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install the dependencies from the project's requirements file, if present:

```bash
pip install -r requirements.txt
```

Check that the BiSeNet model code and pretrained weights are available at the path expected by the current backend configuration. Then start the API using the actual application module path. For example, if the entry point is `app/main.py`:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If the backend entry point is a root-level `main.py`, use the corresponding module path, for example `uvicorn main:app --reload --host 127.0.0.1 --port 8000`. Do not mix these two commands; choose the one that matches the actual repository structure.

Open `http://127.0.0.1:8000/docs` to inspect and test the available endpoints.

### 8.3 Flutter frontend

From the frontend directory:

```bash
flutter pub get
flutter run
```

The frontend's API base URL must point to the backend address reachable from the device running Flutter. `127.0.0.1` works when the frontend can reach the backend on the same host; Android emulators and physical devices may require a different host address. Ensure the backend is running before requesting previews.

### 8.4 HairFastGAN optional setup

The advanced-preview endpoint needs a valid HairFastGAN configuration. The Colab repository must be cloned or uploaded into the runtime, dependencies installed, model weights available, and the code cell importing `hair_swap` run from the correct project directory. If a Cloudflare tunnel is used, its current public URL must be configured in the backend and the tunnel must remain active. A stale tunnel URL will cause connection failures. CPU inference may be substantially slower than GPU inference.

---

## 9. Template Preparation

1. Place hairstyle reference images in the gender-specific template folders expected by the backend.
2. Ensure each template identifier in `library.json` corresponds to an existing image.
3. Annotate the three alignment points in the expected order: left jaw/face point, right jaw/face point, and upper-face point.
4. Keep landmark coordinates consistent with the image size used when the coordinates were created; the current pipeline standardizes relevant images to 512 × 512.
5. Ensure the JSON records contain the fields required by the current selection/alignment code, such as gender, points, face-width ratio, and hair-density score.
6. Use the attribute-calculation helper only when its input paths and coordinate assumptions match the current template data.

Template metadata, paths, and landmark order must agree. A mismatch can cause incorrect variant selection, failed template loading, or poor alignment.

---

## 10. Testing and Validation

The prototype codebase includes test/helper scripts for individual stages, including:
- Variant selection (`test_selection.py`).
- Template alignment (`test_alignment.py`).
- Hair segmentation and blending (`test_blending.py`).
- Feedback workflow (`test_feedback_flow.py`).
- Alignment evaluation (`run_validation.py` / alignment-metric endpoint, depending on the repository version).

Recommended validation sequence:
1. Confirm that the backend health route responds and the BiSeNet model loads.
2. Test face landmark detection on a clear, front-facing photograph.
3. Inspect the generated user and template hair masks.
4. Confirm that the selected template exists and the three alignment points are valid.
5. Inspect the warped template/hair layer and intermediate masks.
6. Confirm that the final preview and before/after comparison are saved and served correctly.
7. Submit `like` and `dislike` feedback and check that records appear in SQLite.
8. Run the fixed-reference alignment evaluation and record the actual values returned by the current backend.
9. Test advanced HairFastGAN preview separately because it depends on external model/runtime availability.

Do not report an evaluation number unless it was produced by the current code using the stated reference inputs. NME and error-reduction values depend on the reference landmarks and normalizer.

---

## 11. Known Limitations and Future Improvements

- **Prototype recommendation metadata:** Some ranked styles and confidence-like values are mock data intended to connect this component with Component 3. They are not proof of a fully trained end-to-end ranking model.
- **Feature matching:** The template selector uses a small number of hand-engineered features and Euclidean distance. Improve it with reliable user-specific measurements, more diverse template data, and evaluation on representative users.
- **Hair-mask errors:** BiSeNet segmentation can fail with unusual lighting, occlusion, hats, extreme angles, hairstyles outside the training distribution, or low-resolution photos.
- **Preview realism:** The standard preview is based on template alignment, masking, inpainting, and alpha blending. Hair texture, lighting, skin boundaries, occlusion, and perspective may not match perfectly.
- **Beard support:** The updated preview pipeline reports that beard-specific segmentation/blending is not implemented in the same way as hairstyle preview.
- **Explanation quality:** Explanations are rule-based and can use mock attribution values. They should not be presented as validated AI reasoning or a professional grooming guarantee.
- **Feedback learning:** Feedback is stored, but the current code does not automatically retrain a model or change similarity weights based on feedback.
- **Advanced preview:** HairFastGAN requires a correctly configured runtime, model weights, dependencies, and a reachable API/tunnel. The Colab integration needs an end-to-end success test before it can be claimed as operational.
- **Alignment evaluation:** Fixed-reference NME tests only the saved comparison setup. The result does not automatically generalize to every uploaded photograph or every hairstyle.
- **Security and production readiness:** Configure CORS, authentication, upload validation, file size limits, temporary-file handling, and user privacy controls before production deployment. The prototype should not be assumed production-hardened.

Potential future work includes connecting the final Component 3 recommendation output, improving template diversity, refining hairline/face geometry, adding a dedicated beard pipeline, testing with varied real-world photos, automating repeatable quantitative evaluation, and stabilizing the HairFastGAN service integration.

---

## 12. Summary of Component 4 Contributions

The component brings together:
- Flutter interface for photo upload, preview presentation, before/after viewing, feedback, and alignment metrics.
- FastAPI endpoints that connect the frontend to the image-processing and feedback workflows.
- Pretrained PyTorch/BiSeNet hair segmentation.
- MediaPipe facial landmark extraction.
- JSON-based hairstyle template metadata and feature-distance variant selection.
- OpenCV affine alignment, mask processing, inpainting, blending, image saving, and before/after comparison.
- Short rule-based recommendation explanations.
- SQLite storage and retrieval of user feedback.
- Fixed-reference landmark alignment evaluation using NME and error-reduction calculations.
- An optional HairFastGAN advanced-preview integration whose availability depends on its runtime configuration.

This component is a prototype that demonstrates an end-to-end hairstyle recommendation and template-preview workflow. Its current outputs and metrics should be interpreted within the limitations described above.
