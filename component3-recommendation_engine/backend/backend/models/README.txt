Gender-aware Component 3 model package.

Models:
- hair_ranker_gender_aware.cbm
- beard_ranker_gender_aware.cbm
- grooming_ranker_gender_aware.cbm
- compatibility_scorer_gender_aware.cbm

Gender is used as a categorical model input.
Female beard rows are excluded by the eligibility rule.
Hair and grooming support both male and female profiles.
Evaluation is reported separately by gender.
Ratings are generated from provisional rules, so results measure
agreement with those rules rather than human suitability accuracy.
Confidence calibration has not been performed.
