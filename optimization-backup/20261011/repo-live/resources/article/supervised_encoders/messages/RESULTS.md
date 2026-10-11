# Supervised message results

Medians over three initialization seeds. Primary macro AUROC averages the five event tasks with at least 30 positives and negatives in the test split. Related message templates may cross splits; this is not a held-out-game evaluation.

| Encoder | Buckets | Width | Parameters | Primary macro AUROC |
|---|---:|---:|---:|---:|
| cnn | — | 32 | 20872 | 0.9945 |
| cnn | — | 128 | 55528 | 0.9997 |
| cnn | — | 256 | 101736 | 1.0000 |
| trigram | 256 | 32 | 9544 | 0.9564 |
| trigram | 256 | 128 | 38056 | 0.9950 |
| trigram | 256 | 256 | 76072 | 0.9964 |
| trigram | 1024 | 32 | 34120 | 0.9769 |
| trigram | 1024 | 128 | 136360 | 0.9989 |
| trigram | 1024 | 256 | 272680 | 0.9996 |
| trigram | 4096 | 32 | 132424 | 0.9859 |
| trigram | 4096 | 128 | 529576 | 0.9996 |
| trigram | 4096 | 256 | 1059112 | 0.9999 |

Individual tasks and all seed values are in results.json. Prayer has no examples and is unscored; hunger, condition, experience and species evaluations have small test samples.
