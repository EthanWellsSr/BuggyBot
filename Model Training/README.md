# Model Training

Training code for the traffic-sign classifier (Self-Driving RC Car).

Current status: a CNN trained on GTSRB (German signs) reaching **~95% validation
accuracy**. Trained model committed as `gtsrb_model.keras`.

The LISA source dataset contains 47 US traffic-sign classes. The current
model-specific dataset retains 12 selected classes. Download and preparation
instructions are in [`LISA_PREPARATION.md`](LISA_PREPARATION.md). The preparation
script is `prepare_lisa.py`; model training and testing are intentionally separate.

## Setup

Requires **Python 3.12** (TensorFlow has no wheels for 3.13/3.14 yet). From this
folder:

```
python3.12 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install tensorflow
```

## Train

```
python training.py
```

Loads `GTSRB/Train/` (80/20 train/validation split), trains a small CNN for 10
epochs, and saves the result to `gtsrb_model.keras`. Runs on CPU in a couple of
minutes.

The model: `Rescaling → Conv2D(32) → MaxPool → Conv2D(64) → MaxPool → Flatten →
Dense(128) → Dense(43, softmax)`, 32×32 input, Adam optimizer.


## Dataset: GTSRB (German Traffic Sign Recognition Benchmark)

The dataset is **not** committed to the repo (too large; publicly re-downloadable).
To set it up:

1. Make a free Kaggle account.
2. Download the ZIP from
   https://www.kaggle.com/datasets/meowmeowmeowmeowmeow/gtsrb-german-traffic-sign?resource=download
   (the "Download" button).
3. Unzip it into `Model Training/GTSRB/` so the layout is:

   ```
   Model Training/GTSRB/
       Train/       43 class folders (0-42), images inside  <- used for training
       Test/        12,631 flat images; labels in Test.csv  <- final testing later
       Meta/        one reference image per sign class
       Train.csv  Test.csv  Meta.csv
   ```

`GTSRB/` is gitignored.
