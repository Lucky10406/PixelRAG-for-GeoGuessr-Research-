## 5. Results

### 5.1 Image-only PixelRAG retrieval

We evaluated PixelRAG on a frozen benchmark of 150 GeoGuessr images spanning 30 countries. For each image, the system retrieved the top five visually similar documents from the hosted PixelRAG index. Country evidence was counted only when the retrieved document title contained a strict country-name match, avoiding broad aliases that could produce false matches such as treating “North Korea” as evidence for South Korea.

The image-only baseline produced correct country evidence in the top five results for **26 of 150 images (17.3%)**. The first correct piece of evidence appeared across all five ranks: 7 cases at rank 1, 2 at rank 2, 5 at rank 3, 5 at rank 4, and 7 at rank 5. Thus, most images did not receive an explicit correct-country signal from the retrieved documents.

A deterministic rank-weighted reader was then applied to the retrieved titles. It produced a country prediction for 51 of 150 images (34.0% coverage). Among all 150 images, **26 predictions were correct and 25 were incorrect**, giving an overall accuracy of **17.3%** and a selective accuracy of **51.0%** on cases where the reader made a prediction. The remaining 99 images resulted in `UNKNOWN`.

These results indicate that PixelRAG can occasionally retrieve geographically informative evidence, but visual retrieval alone is sparse and frequently produces generic, unrelated, or geographically misleading documents.

### 5.2 Text-aware retrieval

To investigate whether visible text could provide a complementary retrieval signal, we added a conservative OCR pipeline using EasyOCR. The pipeline cropped the central gameplay region, filtered common interface text and low-confidence OCR output, and issued a PixelRAG text query only when potentially useful text remained.

The OCR pipeline processed all **150 images**, but only **3 images (2.0%)** produced text that passed the usefulness filters. The remaining **147 images (98.0%)** were treated as having no useful OCR text. This low coverage is an important limitation of the text-aware approach.

The three successful OCR cases produced the following signals:

* **France:** OCR produced `liledeFrance moblites` and `Hybride`. The text-aware query retrieved France-specific documents, including *Plug-in electric vehicles in France*, at ranks 3 and 4. The image-only retrieval contained no correct France evidence. This represents a **text-added correct retrieval**.
* **South Korea:** OCR produced `KOREA` and `coffee`. The text query retrieved *Coffee in South Korea* multiple times, but also retrieved *North Korean cuisine*. Under the strict country matching criterion, this was not counted as correct South Korea evidence.
* **Uganda:** OCR produced `REAL TASK`. The resulting documents were unrelated to Uganda, indicating that OCR can successfully extract text without that text necessarily carrying geographic information.

### 5.3 Image-only versus text-aware retrieval

We directly compared the three successful OCR cases with their corresponding image-only retrievals. **None of the three images had correct country evidence in the image-only top five.** The text-aware pipeline added correct country evidence for **1 of the 3 cases (33.3%)**, while the remaining **2 of 3 cases produced no correct country evidence**.

Thus, within the small subset where the OCR pipeline produced usable text:

* Image-only correct evidence: **0/3**
* Text-aware correct evidence: **1/3**
* Text-added correct evidence: **1/3**
* Neither approach correct: **2/3**

The result is encouraging as a proof of concept: targeted text retrieval can recover geographic evidence that was absent from visual retrieval. However, because useful OCR text was obtained from only **3/150 images (2.0%)**, this experiment does **not** establish an improvement in overall geolocation accuracy.

### 5.4 Failure patterns and limitations

The retrieval analysis shows several recurring failure modes. Many retrieved documents were generic mapping or Street View material, while others were related to roads, transportation, landmarks, or visually similar geographic settings without providing evidence for the correct country. In some cases, the system retrieved geographically related but incorrect evidence. These categories were generated as preliminary automated failure labels and should therefore be interpreted as diagnostic rather than human-validated annotations.

The deterministic reader also demonstrated a key limitation of converting retrieval into predictions: an explicit country-related document can still correspond to the wrong country. For example, retrieval of documents about North Korea for a South Korea image illustrates why strict country matching was necessary. Similarly, road-related pages from another country can create plausible but incorrect country predictions.

The text-aware experiment has additional limitations. First, OCR coverage was extremely low under the conservative filtering pipeline. Second, extracted text was sometimes noisy or non-geographic, as demonstrated by `REAL TASK`. Third, even apparently useful text such as `KOREA` is not always sufficiently specific to distinguish the target country. Finally, the text-aware comparison contains only three successful OCR cases, making the **1/3 success rate a qualitative proof-of-concept result rather than a statistically reliable estimate**.

Overall, the experiments suggest that PixelRAG provides a useful visual retrieval foundation but that its retrieved evidence is often insufficient for direct geolocation. Text-aware retrieval shows potential as a complementary mechanism when visible text contains a strong geographic clue, while also exposing OCR coverage and text disambiguation as important bottlenecks for future work.
