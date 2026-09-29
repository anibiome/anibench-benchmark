# Hypothetical activity and cognition collection

Run `anibench cross-domain-collection input.json --out NEW_RESULT.json`.

The measurement definitions come from UK Biobank fields90012 and20023, linked in
the input metadata and the [method](../../docs/CROSS_DOMAIN_COLLECTION.md).
Every population/model/design number in this example is stipulated. This is
neither UK Biobank participant data nor a UK Biobank benchmark score.

The example has linked digital and cognitive measurements, without an identified
intervention. Removing their participant overlap must remove relationship support
while preserving supported marginal measurements. Changing the observer domain
label alone cannot improve numerical precision. Those are executable tests.
