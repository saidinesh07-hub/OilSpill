# Machine Learning & Remote Sensing Segmentation Pipeline

## 1. Architecture Design: DeepLabV3+ with ASPP
The primary segmentation architecture is **DeepLabV3+**, tailored for student-grade compute budgets (trainable on single GPU / Colab T4):
- **Backbone**: ResNet-34 / ResNet-50 with lightweight convolutional blocks.
- **Atrous Spatial Pyramid Pooling (ASPP)**: Multi-scale context aggregation using atrous convolution rates of 6, 12, and 18 to capture both elongated thin slick tails and broad core plumes.
- **Decoder**: Concatenates ASPP 4x bilinear upsampled features with 1x1 projected low-level spatial features, followed by $3 \times 3$ convolutions and final classification projection into 5 classes.
- **Baseline U-Net**: Available as a lightweight alternative baseline with 4-stage encoder-decoder skip connections.

---

## 2. Loss Formulation: Combined Weighted CE + Soft Dice
Because the ocean surface background occupies over 90% of pixels in SAR scenes, standard Cross-Entropy suffers severe class imbalance. We employ a combined loss:

$$\mathcal{L}_{\text{total}} = \mathcal{L}_{\text{Weighted\_CE}} + \mathcal{L}_{\text{Multiclass\_Dice}}$$

Where class weights $w = [0.2, 3.0, 2.5, 2.0, 1.0]$ heavily prioritize `oil_spill` and `look_alike` discrimination over background `sea_surface`.

---

## 3. Preprocessing & Windowed Tiling
1. **Radiometric Calibration**:
   $$\sigma^0_{\text{dB}} = 10 \cdot \log_{10}\left(\frac{\text{DN}^2}{A_\sigma^2}\right)$$
2. **Speckle Despeckling**: Spatial Lee filter with adaptive variance weighting:
   $$W = \frac{\text{Var}(I)}{\text{Var}(I) + \sigma^2_{\text{noise}}}$$
   $$I_{\text{filtered}} = \bar{I} + W \cdot (I - \bar{I})$$
3. **Overlapping Tiling & Smooth Hann Blending**:
   - Tiling at $256 \times 256$ with 32px stride overlap.
   - Stitching probability fields using a 2D Hann window weighting matrix to eliminate edge seam discontinuities.

---

## 4. Calibrated Confidence & Look-Alike Confusion Index
For every extracted polygon:
- **Calibrated Detection Confidence**: Mean softmax probability over the polygon footprint:
  $$\text{Conf} = \frac{1}{|P|} \sum_{(r, c) \in P} P(\text{class}=1 \mid I_{r, c})$$
- **Look-Alike Confusion Risk**: Cross-entropy confusion index representing probability mass assigned to class 2:
  $$\text{Lookalike\_Risk} = \frac{1}{|P|} \sum_{(r, c) \in P} P(\text{class}=2 \mid I_{r, c})$$
- If $\text{Lookalike\_Risk} > 0.35$, the system flags the detection as a **Moderate-Confidence Potential Slick** rather than falsely claiming a confirmed spill.
