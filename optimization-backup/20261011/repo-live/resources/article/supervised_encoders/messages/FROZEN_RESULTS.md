# Frozen random message encoders

Medians over three initialization seeds. Primary macro AUROC averages the five event tasks with at least 30 positives and negatives in the test split. Related message templates may cross splits; this is not a held-out-game evaluation.

| Encoder | Buckets | Width | Parameters | Primary macro AUROC |
|---|---:|---:|---:|---:|
| cnn | — | 32 | 20872 | 0.8971 |
| cnn | — | 128 | 55528 | 0.9884 |
| cnn | — | 256 | 101736 | 0.9961 |
| trigram | 256 | 32 | 9544 | 0.9572 |
| trigram | 256 | 128 | 38056 | 0.9968 |
| trigram | 256 | 256 | 76072 | 0.9990 |
| trigram | 1024 | 32 | 34120 | 0.9480 |
| trigram | 1024 | 128 | 136360 | 0.9966 |
| trigram | 1024 | 256 | 272680 | 0.9993 |
| trigram | 4096 | 32 | 132424 | 0.9611 |
| trigram | 4096 | 128 | 529576 | 0.9963 |
| trigram | 4096 | 256 | 1059112 | 0.9995 |

Individual tasks and all seed values are in results.json. Prayer has no examples and is unscored; hunger, condition, experience and species evaluations have small test samples.
