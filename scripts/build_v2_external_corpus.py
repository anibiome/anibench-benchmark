#!/usr/bin/env python3
"""Compile source-bound AniBench v2 projections for the external comparator corpus.

The legacy ``data/studies`` objects are deliberately not read.  Every emitted
numeric value is declared below with a local content-addressed primary-source
snapshot and an exact locator.  Missing information remains typed unknown.
The public projections expose the current six-family coordinate boundary, but
never infer protocol-capacity matrices or ranks from descriptive source facts.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from scripts.verify_external_field_receipts import (
        DOWNGRADE_REASON_CODE,
        RECEIPT_CONTRACT as FIELD_RECEIPT_CONTRACT,
        build_field_provenance_receipt,
        enforce_machine_resolved_known_facts,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from verify_external_field_receipts import (  # type: ignore[no-redef]
        DOWNGRADE_REASON_CODE,
        RECEIPT_CONTRACT as FIELD_RECEIPT_CONTRACT,
        build_field_provenance_receipt,
        enforce_machine_resolved_known_facts,
    )


ROOT = Path(__file__).resolve().parents[1]
PROJECTION_ROOT = ROOT / "data" / "source_projections" / "v2"
ACQUISITION_LEDGER = PROJECTION_ROOT / "EXTERNAL_SOURCE_ACQUISITION_LEDGER.json"
PUBLIC_COORDINATE_TABLE = ROOT / "packaging/public_v2/SOURCE_COORDINATE_TABLE.csv"
FIELD_RECEIPT = (
    ROOT / "packaging/public_v2/EXTERNAL_FIELD_PROVENANCE_RECEIPT.json"
)
SOURCE_COORDINATE_CONTRACT = "anibench.source-projection-six-family-coordinates.v1"
FAMILY_IDS = (
    "intensive",
    "extensive",
    "longitudinal",
    "causal",
    "personalized_sequential",
    "transport",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _known(value: Any, source_id: str, locator: str, **metadata: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "state": "known",
        "value": value,
        "is_placeholder": False,
        "source_ids": [source_id],
        "source_locators": {source_id: locator},
    }
    row.update(metadata)
    return row


def _unknown(reason: str, source_ids: list[str], locators: dict[str, str]) -> dict[str, Any]:
    return {
        "state": "unknown",
        "reason": reason,
        "source_ids": source_ids,
        "source_locators": locators,
    }


def _measurement(
    module_id: str,
    lane: str,
    participants: dict[str, Any],
    events: dict[str, Any],
    targets: dict[str, Any],
    completeness: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": module_id,
        "evidence_lane": lane,
        "participants": participants,
        "observation_events": events,
        "targets": targets,
        "completeness": completeness,
    }


def _source(
    source_id: str,
    snapshot: str,
    url: str,
    evidence_class: str,
    locators: list[str],
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "snapshot": snapshot,
        "url": url,
        "evidence_class": evidence_class,
        "locators": locators,
    }


SOURCES: dict[str, dict[str, Any]] = {}


def _register(source: dict[str, Any]) -> str:
    source_id = source["source_id"]
    if source_id in SOURCES:
        raise RuntimeError(f"duplicate source id: {source_id}")
    SOURCES[source_id] = source
    return source_id


CT = {
    "aspree": _register(_source("ctgov-nct01038583", "data/source_projections/v2/sources/clinicaltrials/NCT01038583.json", "https://clinicaltrials.gov/api/v2/studies/NCT01038583", "registry_primary", ["/protocolSection/designModule/enrollmentInfo", "/protocolSection/armsInterventionsModule/armGroups", "/protocolSection/outcomesModule/primaryOutcomes"])),
    "calerie": _register(_source("ctgov-nct00427193", "data/source_projections/v2/sources/clinicaltrials/NCT00427193.json", "https://clinicaltrials.gov/api/v2/studies/NCT00427193", "registry_primary", ["/protocolSection/designModule", "/protocolSection/armsInterventionsModule"])),
    "circulate": _register(_source("ctgov-nct06534450", "data/source_projections/v2/sources/clinicaltrials/NCT06534450.json", "https://clinicaltrials.gov/api/v2/studies/NCT06534450", "registry_primary", ["/protocolSection/designModule", "/protocolSection/armsInterventionsModule"])),
    "dohealth": _register(_source("ctgov-nct01745263", "data/source_projections/v2/sources/clinicaltrials/NCT01745263.json", "https://clinicaltrials.gov/api/v2/studies/NCT01745263", "registry_primary", ["/protocolSection/designModule", "/protocolSection/armsInterventionsModule", "/protocolSection/outcomesModule/primaryOutcomes"])),
    "dq": _register(_source("ctgov-nct04313634", "data/source_projections/v2/sources/clinicaltrials/NCT04313634.json", "https://clinicaltrials.gov/api/v2/studies/NCT04313634", "registry_primary", ["/protocolSection/designModule", "/protocolSection/armsInterventionsModule"])),
    "life": _register(_source("ctgov-nct01072500", "data/source_projections/v2/sources/clinicaltrials/NCT01072500.json", "https://clinicaltrials.gov/api/v2/studies/NCT01072500", "registry_primary", ["/protocolSection/designModule", "/protocolSection/armsInterventionsModule", "/protocolSection/outcomesModule/primaryOutcomes/0/timeFrame"])),
    "mito": _register(_source("ctgov-nct05735886", "data/source_projections/v2/sources/clinicaltrials/NCT05735886.json", "https://clinicaltrials.gov/api/v2/studies/NCT05735886", "registry_primary", ["/protocolSection/designModule", "/protocolSection/armsInterventionsModule"])),
    "motrpac": _register(_source("ctgov-nct03960827", "data/source_projections/v2/sources/clinicaltrials/NCT03960827.json", "https://clinicaltrials.gov/api/v2/studies/NCT03960827", "registry_primary", ["/protocolSection/designModule", "/protocolSection/armsInterventionsModule"])),
    "pearl": _register(_source("ctgov-nct04488601", "data/source_projections/v2/sources/clinicaltrials/NCT04488601.json", "https://clinicaltrials.gov/api/v2/studies/NCT04488601", "registry_primary", ["/protocolSection/designModule", "/protocolSection/armsInterventionsModule"])),
    "predict": _register(_source("ctgov-nct03479866", "data/source_projections/v2/sources/clinicaltrials/NCT03479866.json", "https://clinicaltrials.gov/api/v2/studies/NCT03479866", "registry_primary", ["/protocolSection/designModule", "/protocolSection/outcomesModule/primaryOutcomes"])),
    "sharp": _register(_source("ctgov-nct07596576", "data/source_projections/v2/sources/clinicaltrials/NCT07596576.json", "https://clinicaltrials.gov/api/v2/studies/NCT07596576", "registry_primary", ["/protocolSection/statusModule", "/protocolSection/designModule", "/protocolSection/armsInterventionsModule"])),
    "zoe": _register(_source("ctgov-nct05273268", "data/source_projections/v2/sources/clinicaltrials/NCT05273268.json", "https://clinicaltrials.gov/api/v2/studies/NCT05273268", "registry_primary", ["/protocolSection/designModule", "/protocolSection/armsInterventionsModule"])),
}

PAPER = {
    "aspree": _register(_source("pmc6426126", "data/source_projections/v2/sources/pmc/PMC6426126.bioc.json", "https://pmc.ncbi.nlm.nih.gov/articles/PMC6426126/", "primary_publication_fulltext", ["19,114 persons", "median of 4.7 years"])),
    "calerie_clock": _register(_source("pmc10148951", "data/source_projections/v2/sources/pmc/PMC10148951.bioc.json", "https://pmc.ncbi.nlm.nih.gov/articles/PMC10148951/", "primary_publication_fulltext", ["n = 197 participants", "n = 105 (82%) CR participants and n = 59 (86%) AL participants"])),
    "calerie_resource": _register(_source("pmc11370476", "data/source_projections/v2/sources/pmc/PMC11370476.bioc.json", "https://pmc.ncbi.nlm.nih.gov/articles/PMC11370476/", "primary_publication_fulltext", ["n=218 participants", "total sample n=2327", "SNP data were available for 216 participants"])),
    "circulate": _register(_source("pmc12341816", "data/source_projections/v2/sources/pmc/PMC12341816.bioc.json", "https://pmc.ncbi.nlm.nih.gov/articles/PMC12341816/", "primary_publication_fulltext", ["we enrolled 44 people", "42 completed the study", "longitudinally profile 30 individuals"])),
    "dohealth": _register(_source("pubmed39900648", "data/source_projections/v2/sources/pubmed/39900648.bioc.json", "https://pubmed.ncbi.nlm.nih.gov/39900648/", "primary_publication_abstract", ["777 participants", "over 3 years"])),
    "dq": _register(_source("pubmed38956196", "data/source_projections/v2/sources/pubmed/38956196.bioc.json", "https://pubmed.ncbi.nlm.nih.gov/38956196/", "primary_publication_abstract", ["n = 60 participants", "at 20 weeks"])),
    "life": _register(_source("pmc4266388", "data/source_projections/v2/sources/pmc/PMC4266388.bioc.json", "https://pmc.ncbi.nlm.nih.gov/articles/PMC4266388/", "primary_publication_fulltext", ["1635 sedentary men and women", "median follow-up of 2.6 years"])),
    "mito": _register(_source("pmc12618261", "data/source_projections/v2/sources/pmc/PMC12618261.bioc.json", "https://pmc.ncbi.nlm.nih.gov/articles/PMC12618261/", "primary_publication_fulltext", ["Fifty participants", "five participants before and after both interventions", "231,079 cells"])),
    "motrpac": _register(_source("pmc13184684", "data/source_projections/v2/sources/pmc/PMC13184684.bioc.json", "https://pmc.ncbi.nlm.nih.gov/articles/PMC13184684/", "primary_publication_fulltext", ["N=175", "A total of 176 participants completed the baseline acute test", "174 of 175 participants had Illumina whole genome sequencing"])),
    "pearl": _register(_source("pmc12074816", "data/source_projections/v2/sources/pmc/PMC12074816.bioc.json", "https://pmc.ncbi.nlm.nih.gov/articles/PMC12074816/", "primary_publication_fulltext", ["A total of 114 participants completed", "n = 24", "n = 81"])),
    "predict": _register(_source("pmc8265154", "data/source_projections/v2/sources/pmc/PMC8265154.bioc.json", "https://pmc.ncbi.nlm.nih.gov/articles/PMC8265154/", "primary_publication_fulltext", ["1,002 generally healthy adults", "100 healthy adults", "subsequent 13-days at home"])),
    "snyder": _register(_source("pmc6666404", "data/source_projections/v2/sources/pmc/PMC6666404.bioc.json", "https://pmc.ncbi.nlm.nih.gov/articles/PMC6666404/", "primary_publication_fulltext", ["106 participants", "1,092 time points", "median of 1.6 years per participant"])),
    "snyder_age": _register(_source("pmc7301912", "data/source_projections/v2/sources/pmc/PMC7301912.bioc.json", "https://pmc.ncbi.nlm.nih.gov/articles/PMC7301912/", "primary_publication_fulltext", ["106 healthy individuals", "43 participants"])),
    "triim": _register(_source("pmc6826138", "data/source_projections/v2/sources/pmc/PMC6826138.bioc.json", "https://pmc.ncbi.nlm.nih.gov/articles/PMC6826138/", "primary_publication_fulltext", ["7 of 9 volunteers", "866,836 CpG sites", "months 0–12"])),
    "zoe": _register(_source("pmc11271409", "data/source_projections/v2/sources/pmc/PMC11271409.bioc.json", "https://pmc.ncbi.nlm.nih.gov/articles/PMC11271409/", "primary_publication_fulltext", ["Participants (n = 347)", "PDP (n = 177) or control (n = 170)", "baseline, week 12 and week 18"])),
    "ukb_protocol": _register(_source("pmc4380465", "data/source_projections/v2/sources/pmc/PMC4380465.bioc.json", "https://pmc.ncbi.nlm.nih.gov/articles/PMC4380465/", "primary_resource_publication_fulltext", ["500,000 participants"])),
    "ukb_wgs": _register(_source("pmc12443626", "data/source_projections/v2/sources/pmc/PMC12443626.bioc.json", "https://pmc.ncbi.nlm.nih.gov/articles/PMC12443626/", "primary_resource_publication_fulltext", ["490,640 UK Biobank participants"])),
    "ukb_imaging": _register(_source("pmc7250878", "data/source_projections/v2/sources/pmc/PMC7250878.bioc.json", "https://pmc.ncbi.nlm.nih.gov/articles/PMC7250878/", "primary_resource_publication_fulltext", ["re-inviting 100,000 participants"])),
    "ukb_proteome": _register(_source("pmc10567551", "data/source_projections/v2/sources/pmc/PMC10567551.bioc.json", "https://pmc.ncbi.nlm.nih.gov/articles/PMC10567551/", "primary_resource_publication_fulltext", ["54,219 UKB participants", "2,923 unique proteins"])),
}

AOU = _register(_source("aou-cdrv9-official", "data/source_projections/v2/sources/official/all-of-us-cdrv9.zendesk.json", "https://support.researchallofus.org/hc/en-us/articles/50653909888788-Our-Largest-Genomic-Dataset-Curated-Data-Repository-version-9", "official_release_api_object", ["more than 747,000 participants", "more than 68,000 participants", "Over 535,000 participants"] ))


STUDIES: dict[str, dict[str, Any]] = {}


def _add(study_id: str, **spec: Any) -> None:
    if study_id in STUDIES:
        raise RuntimeError(f"duplicate study: {study_id}")
    STUDIES[study_id] = spec


_add(
    "all-of-us-cdrv9",
    name="NIH All of Us Curated Data Repository v9",
    evaluation_mode="official_dataset_release",
    lifecycle="released_controlled_and_registered_tier_resource",
    source_ids=[AOU],
    population={
        "released_participants_lower_bound": _known(747000, AOU, "article.body: 'more than 747,000 participants'", value_semantics="strict_lower_bound"),
        "exact_released_participants": _unknown("The official release reports a lower bound, not an exact denominator.", [AOU], {AOU: "article.body: 'more than 747,000 participants'"}),
    },
    timeline={
        "followup_duration_days": _unknown("CDRv9 is an accumulating longitudinal resource; one universal participant follow-up duration is not published.", [AOU], {AOU: "release overview"}),
    },
    design=dict(policy_arms=_known(0, AOU, "official release describes a data resource, not assigned interventions"), randomized=_known(False, AOU, "official release describes observational participant data"), control=_known(False, AOU, "no assigned concurrent comparator"), operators=_known(0, AOU, "no assigned intervention operators"), contrasts=_known(0, AOU, "no assigned policy contrast"), adaptive=_known(False, AOU, "no intervention reassignment"), within_policy=_known(False, AOU, "no intervention policy")),
    personalization=dict(individual_state_models=_known(False, AOU, "release inventory; no prospective individual policy"), adaptive_decisions=_known(False, AOU, "release inventory; no prospective individual policy"), randomized_component_personalization=_known(False, AOU, "release inventory; no prospective individual policy"), within_person_counterfactuals=_known(False, AOU, "no randomized within-person intervention"), biological_feedback=_known(False, AOU, "data resource rather than feedback trial"), prospective_policy_evaluation=_known(False, AOU, "data resource rather than policy trial")),
    measurements=[
        _measurement("survey", "official_release_lower_bound", _known(747000, AOU, "article.body: survey data from more than 747,000 participants", value_semantics="strict_lower_bound"), _unknown("Participant-level survey event counts vary and are not frozen in the release note.", [AOU], {AOU: "Overview of Updates"}), _unknown("The release note does not state one frozen survey-variable count.", [AOU], {AOU: "Overview of Updates"}), _unknown("A lower-bound participant count is not module completeness.", [AOU], {AOU: "Overview of Updates"})),
        _measurement("physical_measurements", "official_release_lower_bound", _known(600000, AOU, "article.body: physical measurement data from more than 600,000 participants", value_semantics="strict_lower_bound"), _unknown("Per-participant event counts are not stated.", [AOU], {AOU: "Overview of Updates"}), _unknown("Variable inventory requires the CDR data dictionary.", [AOU], {AOU: "Overview of Updates"}), _unknown("No exact eligible denominator is stated.", [AOU], {AOU: "Overview of Updates"})),
        _measurement("electronic_health_records", "official_release_lower_bound", _known(481000, AOU, "article.body: EHR data from more than 481,000 participants", value_semantics="strict_lower_bound"), _unknown("EHR event counts are participant-specific.", [AOU], {AOU: "Overview of Updates"}), _unknown("No universal code count is frozen.", [AOU], {AOU: "Overview of Updates"}), _unknown("No exact eligible denominator is stated.", [AOU], {AOU: "Overview of Updates"})),
        _measurement("whole_genome_sequence", "official_release_lower_bound", _known(535000, AOU, "article.body: over 535,000 participants with whole genome sequencing", value_semantics="strict_lower_bound"), _known(1, AOU, "one participant genome release object", unit="per_participant_genome"), _known(1, AOU, "whole genome", unit="genome_assay_family"), _unknown("A lower-bound participant count is not exact assay completeness.", [AOU], {AOU: "Overview of Updates"})),
        _measurement("fitbit", "official_release_lower_bound", _known(68000, AOU, "article.body: Fitbit data from more than 68,000 participants", value_semantics="strict_lower_bound"), _unknown("Wear duration and daily completeness vary.", [AOU], {AOU: "Expanded sleep data"}), _unknown("The release note does not freeze a raw observer inventory.", [AOU], {AOU: "Expanded sleep data"}), _unknown("No exact wearable-eligible denominator or completeness threshold is stated.", [AOU], {AOU: "Expanded sleep data"})),
    ],
    classes=dict(exact=["survey", "physical_measurements", "electronic_health_records", "whole_genome_sequence", "fitbit"], conditional=[], unknown=[]),
    validation=dict(state="not_a_model_validation_claim", reason="CDRv9 is a reusable observational data release."),
    access=dict(state="controlled_or_registered_workbench", source_ids=[AOU], reason="Release is available through the Researcher Workbench under tiered access."),
    open_gates=["exact_module_denominators", "participant_event_schedule_export", "crossmodal_joint_denominators", "source_bound_noise_and_design_operators"],
)


_add(
    "uk-biobank",
    name="UK Biobank",
    evaluation_mode="accessible_longitudinal_resource",
    lifecycle="ongoing_population_resource",
    source_ids=[PAPER["ukb_protocol"], PAPER["ukb_wgs"], PAPER["ukb_imaging"], PAPER["ukb_proteome"]],
    population={
        "cohort_enrollment": _known(500000, PAPER["ukb_protocol"], "passage containing '500,000 participants'", value_semantics="reported_cohort_size"),
        "wgs_participants": _known(490640, PAPER["ukb_wgs"], "title and abstract: '490,640 UK Biobank participants'"),
    },
    timeline={"followup_duration_days": _unknown("Follow-up is continuing and participant-specific; no universal duration is used.", [PAPER["ukb_protocol"]], {PAPER["ukb_protocol"]: "long-term follow-up resource description"})},
    design=dict(policy_arms=_known(0, PAPER["ukb_protocol"], "prospective observational resource design"), randomized=_known(False, PAPER["ukb_protocol"], "prospective observational resource design"), control=_known(False, PAPER["ukb_protocol"], "no assigned concurrent comparator"), operators=_known(0, PAPER["ukb_protocol"], "no trial operator assignment"), contrasts=_known(0, PAPER["ukb_protocol"], "no assigned policy contrasts"), adaptive=_known(False, PAPER["ukb_protocol"], "no intervention reassignment"), within_policy=_known(False, PAPER["ukb_protocol"], "no intervention policy")),
    personalization=dict(individual_state_models=_known(False, PAPER["ukb_protocol"], "resource protocol, not prospective personalized policy"), adaptive_decisions=_known(False, PAPER["ukb_protocol"], "resource protocol"), randomized_component_personalization=_known(False, PAPER["ukb_protocol"], "resource protocol"), within_person_counterfactuals=_known(False, PAPER["ukb_protocol"], "no randomized within-person operator"), biological_feedback=_known(False, PAPER["ukb_protocol"], "no prospective feedback intervention"), prospective_policy_evaluation=_known(False, PAPER["ukb_protocol"], "no prospective policy comparison")),
    measurements=[
        _measurement("whole_genome_sequence", "realized_resource", _known(490640, PAPER["ukb_wgs"], "title/abstract denominator"), _known(1, PAPER["ukb_wgs"], "one WGS profile per participant", unit="per_participant_genome"), _known(1, PAPER["ukb_wgs"], "whole-genome sequencing", unit="assay_family"), _unknown("The WGS publication denominator is not a universal completeness fraction against every UKB participant.", [PAPER["ukb_wgs"]], {PAPER["ukb_wgs"]: "Cohorts section"})),
        _measurement("multimodal_imaging", "planned_resource_target", _known(100000, PAPER["ukb_imaging"], "abstract: aim of re-inviting 100,000 participants", value_semantics="planned_target_not_realized_count"), _known(1, PAPER["ukb_imaging"], "one baseline imaging enhancement visit", value_semantics="planned_core_visit"), _known(5, PAPER["ukb_imaging"], "brain, cardiac, abdominal MRI, DXA, carotid ultrasound", unit="imaging_families"), _unknown("The source gives a target, not current realized completeness.", [PAPER["ukb_imaging"]], {PAPER["ukb_imaging"]: "abstract"})),
        _measurement("plasma_proteome", "realized_resource", _known(54219, PAPER["ukb_proteome"], "abstract and Overview: 54,219 UKB participants"), _known(1, PAPER["ukb_proteome"], "baseline plasma profile", unit="baseline_profile"), _known(2923, PAPER["ukb_proteome"], "Overview: 2,923 unique proteins"), _unknown("Subcohort selection and QC prevent a universal cohort completeness claim.", [PAPER["ukb_proteome"]], {PAPER["ukb_proteome"]: "Overview of UKB-PPP characteristics"})),
        _measurement("clinical_phenotype_and_records", "resource_presence_exact_denominator_open", _known(500000, PAPER["ukb_protocol"], "resource cohort size", value_semantics="cohort_scale_not_module_complete"), _unknown("Event counts and follow-up differ by participant.", [PAPER["ukb_protocol"]], {PAPER["ukb_protocol"]: "data linkage and follow-up sections"}), _unknown("The field inventory is versioned in Showcase rather than frozen here.", [PAPER["ukb_protocol"]], {PAPER["ukb_protocol"]: "resource description"}), _unknown("No one module-eligible denominator is stated.", [PAPER["ukb_protocol"]], {PAPER["ukb_protocol"]: "resource description"})),
    ],
    classes=dict(exact=["whole_genome_sequence", "multimodal_imaging", "plasma_proteome"], conditional=[], unknown=["clinical_phenotype_and_records"]),
    validation=dict(state="resource_specific_not_global", reason="Individual downstream models have their own validation; the resource itself has no single model-validation state."),
    access=dict(state="approved_researcher_cloud_access", source_ids=[PAPER["ukb_protocol"]], reason="Access is governed by UK Biobank application and platform procedures."),
    open_gates=["current_data_showcase_snapshot", "exact_crossmodal_joint_denominators", "repeat_assessment_event_export", "source_bound_information_matrices"],
)


_add(
    "snyder-ipop-ihmp-106",
    name="Snyder iPOP / iHMP longitudinal host-microbe cohort",
    evaluation_mode="realized_longitudinal_cohort",
    lifecycle="completed_public_resource",
    source_ids=[PAPER["snyder"], PAPER["snyder_age"]],
    population={"profiled_participants": _known(106, PAPER["snyder"], "Overview: followed 106 participants")},
    timeline={"median_observation_span_days": _known(584, PAPER["snyder"], "Overview: median 1.6 years per participant", derivation="1.6*365", value_semantics="reported_median_years_converted_to_days"), "maximum_observation_span_days": _unknown("The paper reports nearly four years for the cohort and seven years for one person, not one universal maximum-day denominator.", [PAPER["snyder"]], {PAPER["snyder"]: "Overview"})},
    design=dict(policy_arms=_known(0, PAPER["snyder"], "observational longitudinal cohort"), randomized=_known(False, PAPER["snyder"], "natural stress events, not assigned interventions"), control=_known(False, PAPER["snyder"], "no assigned concurrent comparator"), operators=_known(0, PAPER["snyder"], "no assigned operators"), contrasts=_known(0, PAPER["snyder"], "no assigned policy contrast"), adaptive=_known(False, PAPER["snyder"], "no intervention reassignment"), within_policy=_known(False, PAPER["snyder"], "no intervention policy")),
    personalization=dict(individual_state_models=_known(True, PAPER["snyder_age"], "personal aging-marker longitudinal analyses", evidence_scope="retrospective_analysis"), adaptive_decisions=_known(False, PAPER["snyder_age"], "no prospective adaptive operator"), randomized_component_personalization=_known(False, PAPER["snyder"], "no randomized intervention"), within_person_counterfactuals=_known(False, PAPER["snyder"], "dense natural trajectories are not randomized counterfactuals"), biological_feedback=_known(False, PAPER["snyder"], "no prospective feedback policy tested"), prospective_policy_evaluation=_known(False, PAPER["snyder"], "observational cohort")),
    measurements=[
        _measurement("joint_longitudinal_visit_stream", "realized_publication", _known(106, PAPER["snyder"], "Overview cohort"), _known(1092, PAPER["snyder"], "Overview: profiled 1,092 time points", unit="cohort_total_timepoints"), _known(7, PAPER["snyder"], "clinical labs, transcriptome, metabolome, proteome, cytokines, genome, microbiome", unit="module_families"), _unknown("The 1,092 visits have assay-specific missingness; not every module is present at every visit.", [PAPER["snyder"]], {PAPER["snyder"]: "Supplementary Table 3 statement"})),
        _measurement("healthy_baseline_visits", "realized_publication", _known(106, PAPER["snyder"], "cohort denominator"), _known(624, PAPER["snyder"], "Overview: 624 healthy baselines", unit="cohort_total_timepoints"), _unknown("Assay-specific target counts differ by omic.", [PAPER["snyder"]], {PAPER["snyder"]: "Fig. 1c and Supplementary Table 3"}), _unknown("Assay-specific coverage matrix is required.", [PAPER["snyder"]], {PAPER["snyder"]: "Supplementary Table 3"})),
        _measurement("stress_event_visits", "realized_publication", _known(54, PAPER["snyder"], "54 respiratory viral infection episodes", unit="episodes_not_participants"), _known(203, PAPER["snyder"], "203 RVI visits", unit="cohort_total_timepoints"), _unknown("Assay-specific target counts differ by omic.", [PAPER["snyder"]], {PAPER["snyder"]: "Overview"}), _unknown("Episode and participant denominators are not interchangeable.", [PAPER["snyder"]], {PAPER["snyder"]: "Overview"})),
    ],
    classes=dict(exact=["joint_longitudinal_visit_stream", "healthy_baseline_visits", "stress_event_visits"], conditional=[], unknown=[]),
    validation=dict(state="exploratory_longitudinal_models", reason="Retrospective personal and cohort analyses are published; no universal held-person intervention-policy validation is asserted."),
    access=dict(state="public_repository_plus_controlled_exome", source_ids=[PAPER["snyder_age"]], reason="Paper data-availability section routes raw multi-omics and dbGaP exomes."),
    open_gates=["assay_by_participant_by_event_coverage_matrix", "exact_joint_crossmodal_event_denominators", "prospective_intervention_contrast", "source_bound_noise_covariances"],
)


_add(
    "predict-1",
    name="PREDICT 1",
    evaluation_mode="realized_perturbational_cohort",
    lifecycle="completed_primary_and_held_out_validation_cohorts",
    source_ids=[CT["predict"], PAPER["predict"]],
    population={"uk_primary_cohort": _known(1002, PAPER["predict"], "Methods: 1,002 UK adults"), "us_validation_cohort": _known(100, PAPER["predict"], "Methods: 100 US adults"), "combined_profiled": _known(1102, PAPER["predict"], "two source cohorts; derivation 1002+100", derivation="1002+100")},
    timeline={"protocol_duration_days": _known(14, PAPER["predict"], "baseline clinic day plus subsequent 13-day home period")},
    design=dict(policy_arms=_known(1, CT["predict"], "/protocolSection/armsInterventionsModule/armGroups"), randomized=_known(False, CT["predict"], "/protocolSection/designModule/designInfo/allocation = NA"), control=_known(False, CT["predict"], "single-group dietary challenge"), operators=_known(1, CT["predict"], "standardized dietary challenge family"), contrasts=_known(0, CT["predict"], "no randomized policy comparator"), adaptive=_known(False, CT["predict"], "no treatment reassignment"), within_policy=_known(False, CT["predict"], "meal sequence is standardized, not randomized component personalization")),
    personalization=dict(individual_state_models=_known(True, PAPER["predict"], "person-specific postprandial response models", evidence_scope="retrospective_model"), adaptive_decisions=_known(False, PAPER["predict"], "no prospective adaptive decision trial"), randomized_component_personalization=_known(False, CT["predict"], "single-group study"), within_person_counterfactuals=_known(False, PAPER["predict"], "repeat meals are not a randomized N-of-1 policy"), biological_feedback=_known(False, PAPER["predict"], "no prospective returned recommendation policy tested"), prospective_policy_evaluation=_known(False, PAPER["predict"], "model validated observationally in US cohort")),
    measurements=[
        _measurement("clinic_postprandial_challenge", "realized_publication", _known(1002, PAPER["predict"], "Methods UK cohort"), _known(1, PAPER["predict"], "clinic day 1", unit="clinic_challenge_day"), _known(3, PAPER["predict"], "triglyceride, glucose, insulin responses", unit="response_families"), _unknown("Per-analyte usable denominators differ.", [PAPER["predict"]], {PAPER["predict"]: "Figure 2 legend"})),
        _measurement("continuous_glucose", "realized_publication", _known(1002, PAPER["predict"], "UK cohort eligible; usable denominator differs", value_semantics="cohort_scope_not_usable_count"), _known(14, PAPER["predict"], "CGM worn for entire 14-day study", unit="days"), _known(1, PAPER["predict"], "interstitial glucose", unit="continuous_signal"), _unknown("Usable meal and sensor denominators vary; Figure 2 reports outcome-specific n.", [PAPER["predict"]], {PAPER["predict"]: "Figure 2 legend"})),
        _measurement("microbiome_16s", "realized_publication_presence", _unknown("The paper does not state one exact QC-passed participant count in the main text.", [PAPER["predict"]], {PAPER["predict"]: "microbiome Methods and Supplementary Table 1"}), _known(1, PAPER["predict"], "baseline stool specimen", unit="planned_specimen"), _known(1, PAPER["predict"], "16S V4 assay", unit="assay_family"), _unknown("Exact QC denominator requires the data table.", [PAPER["predict"]], {PAPER["predict"]: "Supplementary Table 1"})),
        _measurement("whole_genome_genotype_subset", "realized_publication", _known(241, PAPER["predict"], "Methods: genome-wide genotyping available for n = 241"), _known(1, PAPER["predict"], "prior TwinsUK genotype", unit="per_participant_profile"), _known(1, PAPER["predict"], "genotype assay family"), _unknown("Subset selection is not cohort completeness.", [PAPER["predict"]], {PAPER["predict"]: "Whole genome genotyping Methods"})),
    ],
    classes=dict(exact=["clinic_postprandial_challenge", "continuous_glucose", "whole_genome_genotype_subset"], conditional=[], unknown=["microbiome_16s"]),
    validation=dict(state="held_out_cohort_reported", source_ids=[PAPER["predict"]], primary_training_cohort=1002, held_out_validation_cohort=100, reason="US cohort was independently held out for postprandial response prediction; outcome-specific usable n and calibration remain model-specific."),
    access=dict(state="application_controlled_plus_16s_repository", source_ids=[PAPER["predict"]], reason="Paper data-availability section requires bona fide researcher application for participant-level variables."),
    open_gates=["outcome_specific_usable_denominators", "microbiome_qc_denominator", "participant_event_jointness_export", "source_bound_noise_covariances"],
)


_add(
    "aspree",
    name="ASPirin in Reducing Events in the Elderly",
    evaluation_mode="realized_randomized_trial",
    lifecycle="completed_primary_trial_with_ongoing_followup_resource",
    source_ids=[CT["aspree"], PAPER["aspree"]],
    population={"randomized": _known(19114, PAPER["aspree"], "Abstract/Methods: 19,114 persons")},
    timeline={"median_followup_years": _known(4.7, PAPER["aspree"], "primary publication: median 4.7 years", unit="years"), "followup_duration_days": _unknown("The source reports a median in years, not a universal exact participant duration in days.", [PAPER["aspree"]], {PAPER["aspree"]: "primary results follow-up statement"})},
    design=dict(policy_arms=_known(2, PAPER["aspree"], "aspirin and placebo groups"), randomized=_known(True, PAPER["aspree"], "randomized double-blind placebo-controlled trial"), control=_known(True, PAPER["aspree"], "concurrent placebo"), operators=_known(1, PAPER["aspree"], "100 mg aspirin operator"), contrasts=_known(1, PAPER["aspree"], "primary aspirin-versus-placebo policy contrast"), adaptive=_known(False, PAPER["aspree"], "parallel assignment"), within_policy=_known(False, PAPER["aspree"], "no randomized component adaptation")),
    personalization=dict(individual_state_models=_known(False, PAPER["aspree"], "population-level treatment policy"), adaptive_decisions=_known(False, PAPER["aspree"], "fixed assignment"), randomized_component_personalization=_known(False, PAPER["aspree"], "fixed aspirin dose"), within_person_counterfactuals=_known(False, PAPER["aspree"], "parallel trial"), biological_feedback=_known(False, PAPER["aspree"], "no personalized feedback loop"), prospective_policy_evaluation=_known(True, PAPER["aspree"], "prospective randomized aspirin policy")),
    measurements=[
        _measurement("disability_free_survival", "realized_primary_endpoint", _known(19114, PAPER["aspree"], "randomized population"), _known(2, CT["aspree"], "/protocolSection/outcomesModule/primaryOutcomes/0/timeFrame = every 6 months", unit="scheduled_assessments_per_year"), _known(3, CT["aspree"], "death, incident dementia, persistent physical disability", unit="endpoint_components"), _unknown("Event ascertainment and censoring require participant-level data.", [PAPER["aspree"]], {PAPER["aspree"]: "Methods and primary endpoint"})),
        _measurement("clinical_and_functional_battery", "realized_presence_denominators_open", _unknown("Assay-specific participant denominators are not frozen in the primary paper.", [PAPER["aspree"]], {PAPER["aspree"]: "Methods"}), _unknown("Visit-level battery schedules differ by endpoint.", [CT["aspree"]], {CT["aspree"]: "/protocolSection/outcomesModule"}), _unknown("No single target count is defensible across the battery.", [CT["aspree"]], {CT["aspree"]: "/protocolSection/outcomesModule"}), _unknown("Module completeness requires the trial data dictionary.", [PAPER["aspree"]], {PAPER["aspree"]: "Methods"})),
    ],
    classes=dict(exact=["disability_free_survival"], conditional=[], unknown=["clinical_and_functional_battery"]),
    validation=dict(state="randomized_primary_estimand_reported", reason="The trial estimates aspirin-versus-placebo effects; this is not a biological state reconstruction validation claim."),
    access=dict(state="application_managed", source_ids=[PAPER["aspree"]], reason="Participant-level reuse requires the ASPREE access process."),
    open_gates=["participant_event_schedule_export", "module_specific_denominators", "crossmodal_jointness", "information_operator_and_noise_matrices"],
)


_add(
    "calerie-phase-2-expanded",
    name="CALERIE Phase 2 expanded molecular resource",
    evaluation_mode="realized_randomized_multiomic_resource",
    lifecycle="completed_trial_public_genomic_resource",
    source_ids=[CT["calerie"], PAPER["calerie_clock"], PAPER["calerie_resource"]],
    population={"registry_enrolled": _known(238, CT["calerie"], "/protocolSection/designModule/enrollmentInfo/count"), "randomized": _known(220, PAPER["calerie_resource"], "Of 238 eligible enrolled participants, n=220 were allocated"), "genomic_resource_participants": _known(218, PAPER["calerie_resource"], "genomic datasets from n=218 participants")},
    timeline={"intervention_duration_days": _known(730, PAPER["calerie_resource"], "2-year study", derivation="2*365", value_semantics="protocol_years_converted_to_days")},
    design=dict(policy_arms=_known(2, CT["calerie"], "/protocolSection/armsInterventionsModule/armGroups"), randomized=_known(True, CT["calerie"], "/protocolSection/designModule/designInfo/allocation"), control=_known(True, CT["calerie"], "ad libitum concurrent control arm"), operators=_known(1, CT["calerie"], "caloric restriction operator"), contrasts=_known(1, PAPER["calerie_resource"], "CR versus AL comparison"), adaptive=_known(False, CT["calerie"], "parallel assignment"), within_policy=_known(False, CT["calerie"], "no randomized component adaptation")),
    personalization=dict(individual_state_models=_known(False, PAPER["calerie_resource"], "no individual intervention policy model"), adaptive_decisions=_known(False, PAPER["calerie_resource"], "fixed CR assignment"), randomized_component_personalization=_known(False, PAPER["calerie_resource"], "no randomized personalized components"), within_person_counterfactuals=_known(False, PAPER["calerie_resource"], "parallel assignment"), biological_feedback=_known(True, PAPER["calerie_resource"], "individual counseling and adherence feedback", evidence_scope="adherence_support_not_policy_randomization"), prospective_policy_evaluation=_known(True, PAPER["calerie_resource"], "prospective randomized CR policy")),
    measurements=[
        _measurement("blood_dna_methylation_clock_analysis", "realized_publication", _known(197, PAPER["calerie_clock"], "DNAm baseline plus at least one follow-up"), _known(3, PAPER["calerie_clock"], "baseline, 12 months, 24 months", unit="scheduled_timepoints"), _known(850000, PAPER["calerie_clock"], "EPIC array quantifies >850,000 CpG sites", value_semantics="strict_lower_bound"), _known(164, PAPER["calerie_clock"], "105 CR plus 59 AL with all three timepoints", value_semantics="participants_with_all_three_timepoints", derivation="105+59")),
        _measurement("snp_genotype", "realized_resource", _known(216, PAPER["calerie_resource"], "SNP data available for 216 participants"), _known(1, PAPER["calerie_resource"], "baseline blood", unit="per_participant_profile"), _known(654027, PAPER["calerie_resource"], "Global Screening Array markers", unit="array_markers"), _unknown("The genotype denominator is reported, but a trial-eligible completeness fraction is not used.", [PAPER["calerie_resource"]], {PAPER["calerie_resource"]: "Genotype section"})),
        _measurement("multi_tissue_dnam_rna_resource", "realized_resource", _known(218, PAPER["calerie_resource"], "resource participant count", value_semantics="at_least_one_genomic_dataset"), _known(2327, PAPER["calerie_resource"], "total sample n=2327", unit="cohort_total_assay_samples"), _known(3, PAPER["calerie_resource"], "blood, skeletal muscle, adipose", unit="tissue_families"), _unknown("Coverage varies by tissue, data type, group, and timepoint; Supplementary Table S1 is required.", [PAPER["calerie_resource"]], {PAPER["calerie_resource"]: "sample availability matrix statement"})),
    ],
    classes=dict(exact=["blood_dna_methylation_clock_analysis", "snp_genotype", "multi_tissue_dnam_rna_resource"], conditional=[], unknown=[]),
    validation=dict(state="randomized_trial_plus_resource", reason="Randomized intervention effects are estimable; no held-person general biological reconstruction model is claimed."),
    access=dict(state="application_managed_aging_research_biobank", source_ids=[PAPER["calerie_resource"]], reason="The genomic resource is available through the Aging Research Biobank."),
    open_gates=["supplementary_sample_availability_matrix", "exact_crossmodal_joint_event_graph", "assay_noise_covariances", "held_person_reconstruction_validation"],
)


_add(
    "circulate-tpe-ivig",
    name="CIRCULATE therapeutic plasma exchange with and without IVIG",
    evaluation_mode="realized_randomized_feasibility_trial",
    lifecycle="completed_primary_publication_registry_followup_open",
    source_ids=[CT["circulate"], PAPER["circulate"]],
    population={"registry_enrollment": _known(40, CT["circulate"], "/protocolSection/designModule/enrollmentInfo/count", value_semantics="registry_record"), "paper_enrolled": _known(44, PAPER["circulate"], "Results: enrolled 44 people"), "paper_completed": _known(42, PAPER["circulate"], "Results: 42 completed")},
    timeline={"maximum_intervention_regimen_months": _known(6, CT["circulate"], "monthly arm: 6 monthly procedures", unit="months"), "intervention_duration_days": _unknown("Regimen spans differ by arm and no single exact day duration is reported.", [CT["circulate"], PAPER["circulate"]], {CT["circulate"]: "/protocolSection/armsInterventionsModule/armGroups", PAPER["circulate"]: "study design"})},
    design=dict(policy_arms=_known(4, CT["circulate"], "/protocolSection/armsInterventionsModule/armGroups"), randomized=_known(True, CT["circulate"], "/protocolSection/designModule/designInfo/allocation", caveat="Publication describes entry-date/first-come scheduling; allocation integrity needs audit."), control=_known(True, CT["circulate"], "sham arm"), operators=_known(2, CT["circulate"], "TPE and IVIG active operator families"), contrasts=_unknown("The publication does not freeze one multiplicity-controlled contrast set for all four policies.", [PAPER["circulate"]], {PAPER["circulate"]: "Methods and exploratory analysis"}), adaptive=_known(False, CT["circulate"], "parallel assignment"), within_policy=_known(False, CT["circulate"], "no adaptive component randomization")),
    personalization=dict(individual_state_models=_known(False, PAPER["circulate"], "exploratory response stratification is retrospective"), adaptive_decisions=_known(False, CT["circulate"], "fixed regimen"), randomized_component_personalization=_known(False, CT["circulate"], "fixed arms"), within_person_counterfactuals=_known(False, CT["circulate"], "parallel trial"), biological_feedback=_known(False, PAPER["circulate"], "no prospective feedback policy"), prospective_policy_evaluation=_known(True, CT["circulate"], "prospective group comparison", caveat="allocation mechanism requires audit")),
    measurements=[
        _measurement("multiomics_intervention_cohort", "realized_publication", _known(30, PAPER["circulate"], "longitudinally profile 30 individuals across three TPE modalities"), _known(3, PAPER["circulate"], "blood before sessions 1, 4, and 6", unit="scheduled_timepoints"), _known(7, PAPER["circulate"], "epigenome, proteome, metabolome, lipidome, glycome, cytomics, immune marker families", unit="module_families"), _unknown("Same-sample statement does not establish exact assay-complete joint rows across every omic.", [PAPER["circulate"]], {PAPER["circulate"]: "multi-omics Methods"})),
        _measurement("epigenetic_clocks", "realized_publication", _known(42, PAPER["circulate"], "completed cohort", value_semantics="trial_completers_not_assay_complete_denominator"), _known(3, PAPER["circulate"], "time points 1, 2, 3"), _known(36, PAPER["circulate"], "36 epigenetic clocks", unit="derived_clock_outputs"), _unknown("Assay-specific exclusions and arm-level availability must be read from source tables.", [PAPER["circulate"]], {PAPER["circulate"]: "epigenetic Methods and tables"})),
    ],
    classes=dict(exact=["multiomics_intervention_cohort", "epigenetic_clocks"], conditional=[], unknown=[]),
    validation=dict(state="exploratory_no_external_validation", reason="Small feasibility trial; response-prediction analyses are exploratory and not held-cohort validated."),
    access=dict(state="publication_plus_proteomics_repository", source_ids=[PAPER["circulate"]], reason="Publication provides aggregate results and routes proteomics data; full participant matrix access is not established here."),
    open_gates=["registry_publication_enrollment_reconciliation", "allocation_integrity_audit", "assay_by_event_completeness_matrix", "multiplicity_controlled_estimand_set", "external_validation"],
)


_add(
    "do-health-bio-age",
    name="DO-HEALTH Bio-Age",
    evaluation_mode="realized_factorial_randomized_trial_substudy",
    lifecycle="completed_trial_posthoc_dnam_analysis",
    source_ids=[CT["dohealth"], PAPER["dohealth"]],
    population={"randomized_trial": _known(2157, CT["dohealth"], "/protocolSection/designModule/enrollmentInfo/count"), "paired_dnam_substudy": _known(777, PAPER["dohealth"], "abstract: 777 participants")},
    timeline={"intervention_duration_days": _known(1095, CT["dohealth"], "primary outcomes over 36 months", derivation="36 months interpreted as 3*365 protocol days", value_semantics="protocol_years_converted_to_days")},
    design=dict(policy_arms=_known(8, CT["dohealth"], "/protocolSection/armsInterventionsModule/armGroups"), randomized=_known(True, CT["dohealth"], "/protocolSection/designModule/designInfo/allocation"), control=_known(True, CT["dohealth"], "factorial placebo/flexibility reference policy"), operators=_known(3, CT["dohealth"], "vitamin D, omega-3, strength exercise"), contrasts=_unknown("The post hoc DNAm analysis uses main effects and selected interactions; one scalar contrast count would erase estimand structure.", [PAPER["dohealth"]], {PAPER["dohealth"]: "abstract and analysis description"}), adaptive=_known(False, CT["dohealth"], "fixed factorial assignment"), within_policy=_known(False, CT["dohealth"], "no adaptive component reassignment")),
    personalization=dict(individual_state_models=_known(False, PAPER["dohealth"], "population-level clock analyses"), adaptive_decisions=_known(False, CT["dohealth"], "fixed assignment"), randomized_component_personalization=_known(False, CT["dohealth"], "factorial components are randomized at group level, not personalized"), within_person_counterfactuals=_known(False, CT["dohealth"], "parallel factorial trial"), biological_feedback=_known(False, CT["dohealth"], "no biological feedback policy"), prospective_policy_evaluation=_known(True, CT["dohealth"], "prospective randomized factorial policies")),
    measurements=[
        _measurement("dna_methylation_age", "realized_posthoc_substudy", _known(777, PAPER["dohealth"], "paired samples n=777"), _known(2, PAPER["dohealth"], "baseline and 3-year follow-up", unit="timepoints"), _known(4, PAPER["dohealth"], "PhenoAge, GrimAge, GrimAge2, DunedinPACE", unit="clock_outputs"), _known(777, PAPER["dohealth"], "all analyses used samples of n=777 at baseline and follow-up", value_semantics="paired_participants")),
        _measurement("functional_and_clinical_outcomes", "registry_schedule", _known(2157, CT["dohealth"], "trial enrollment", value_semantics="trial_population_not_complete_module_denominator"), _known(4, CT["dohealth"], "baseline, 12, 24, 36 months", unit="scheduled_timepoints"), _unknown("The registry enumerates outcomes, not one target count.", [CT["dohealth"]], {CT["dohealth"]: "/protocolSection/outcomesModule"}), _unknown("Outcome-specific completeness is not established by registry schedule.", [CT["dohealth"]], {CT["dohealth"]: "/resultsSection if available and publications"})),
    ],
    classes=dict(exact=["dna_methylation_age", "functional_and_clinical_outcomes"], conditional=[], unknown=[]),
    validation=dict(state="randomized_substudy_no_external_model_validation", reason="Factorial effects in a paired DNAm substudy are estimated; no held-cohort biological reconstruction model is asserted."),
    access=dict(state="publication_aggregate_data", source_ids=[PAPER["dohealth"]], reason="Participant-level reuse terms require the DO-HEALTH data process."),
    open_gates=["dnam_substudy_selection_receipt", "arm_by_timepoint_denominators", "exact_joint_clinical_dnam_graph", "frozen_factorial_estimands"],
)


_add(
    "dq-senolytic-bone",
    name="Dasatinib plus quercetin senolytic bone trial",
    evaluation_mode="realized_randomized_trial_publication_subset",
    lifecycle="completed_trial_primary_dq_analysis",
    source_ids=[CT["dq"], PAPER["dq"]],
    population={"registry_enrollment": _known(74, CT["dq"], "/protocolSection/designModule/enrollmentInfo/count"), "primary_publication_dq_comparison": _known(60, PAPER["dq"], "abstract: n = 60 participants")},
    timeline={"intervention_duration_days": _known(140, CT["dq"], "20 weeks", derivation="20*7")},
    design=dict(policy_arms=_known(3, CT["dq"], "/protocolSection/armsInterventionsModule/armGroups"), randomized=_known(True, CT["dq"], "/protocolSection/designModule/designInfo/allocation"), control=_known(True, CT["dq"], "untreated control arm"), operators=_known(2, CT["dq"], "D+Q and fisetin operator policies"), contrasts=_unknown("The n=60 paper reports D+Q versus control while the registry has three arms; a full estimand set is not frozen.", [CT["dq"], PAPER["dq"]], {CT["dq"]: "/protocolSection/armsInterventionsModule", PAPER["dq"]: "abstract"}), adaptive=_known(False, CT["dq"], "parallel assignment"), within_policy=_known(False, CT["dq"], "fixed dosing")),
    personalization=dict(individual_state_models=_known(False, PAPER["dq"], "high p16 subgroup is exploratory, not prospective policy"), adaptive_decisions=_known(False, CT["dq"], "fixed assignment"), randomized_component_personalization=_known(False, CT["dq"], "no personalized component randomization"), within_person_counterfactuals=_known(False, CT["dq"], "parallel trial"), biological_feedback=_known(False, PAPER["dq"], "no prospective feedback"), prospective_policy_evaluation=_known(True, CT["dq"], "prospective randomized intervention")),
    measurements=[
        _measurement("bone_turnover_markers", "realized_primary_publication", _known(60, PAPER["dq"], "publication trial n=60"), _known(4, PAPER["dq"], "baseline, weeks 2, 4, and 20", unit="reported_timepoints"), _known(2, PAPER["dq"], "CTx and P1NP", unit="primary_secondary_markers"), _unknown("Marker-specific missingness is not stated in the abstract source.", [PAPER["dq"]], {PAPER["dq"]: "abstract"})),
        _measurement("skeletal_imaging_and_p16", "presence_denominator_open", _unknown("Exact imaging and p16 participant-event denominators require full tables/supplement.", [PAPER["dq"]], {PAPER["dq"]: "exploratory subgroup and radius BMD results"}), _unknown("Schedules differ between p16 and imaging.", [PAPER["dq"]], {PAPER["dq"]: "publication Methods"}), _known(2, PAPER["dq"], "p16 burden and radius BMD", unit="module_families"), _unknown("Subset completeness is not source-established in the preserved abstract.", [PAPER["dq"]], {PAPER["dq"]: "abstract"})),
    ],
    classes=dict(exact=["bone_turnover_markers"], conditional=[], unknown=["skeletal_imaging_and_p16"]),
    validation=dict(state="exploratory_subgroup_not_validated", reason="High-p16 treatment-effect heterogeneity is exploratory and not prospectively validated."),
    access=dict(state="publication_aggregate", source_ids=[PAPER["dq"]], reason="Preserved public sources do not establish participant-level matrix access."),
    open_gates=["registry_paper_population_reconciliation", "three_arm_estimand_set", "full_supplement_snapshot", "participant_event_denominators", "prospective_subgroup_validation"],
)


_add(
    "life-study",
    name="Lifestyle Interventions and Independence for Elders",
    evaluation_mode="realized_randomized_trial",
    lifecycle="completed_trial_biobank_resource",
    source_ids=[CT["life"], PAPER["life"]],
    population={"randomized": _known(1635, CT["life"], "/protocolSection/designModule/enrollmentInfo/count")},
    timeline={"average_followup_years": _known(2.6, CT["life"], "/protocolSection/outcomesModule/primaryOutcomes/0/timeFrame", unit="years"), "followup_duration_days": _unknown("Average years are not an exact universal participant duration in days.", [CT["life"]], {CT["life"]: "/protocolSection/outcomesModule/primaryOutcomes/0/timeFrame"})},
    design=dict(policy_arms=_known(2, CT["life"], "/protocolSection/armsInterventionsModule/armGroups"), randomized=_known(True, CT["life"], "/protocolSection/designModule/designInfo/allocation"), control=_known(True, CT["life"], "successful-aging concurrent policy"), operators=_known(1, CT["life"], "structured physical activity operator"), contrasts=_known(1, CT["life"], "physical activity versus successful aging"), adaptive=_known(False, CT["life"], "parallel assignment"), within_policy=_known(False, CT["life"], "no adaptive component randomization")),
    personalization=dict(individual_state_models=_known(False, PAPER["life"], "population intervention"), adaptive_decisions=_known(False, CT["life"], "fixed assignment"), randomized_component_personalization=_known(False, CT["life"], "no personalized randomization"), within_person_counterfactuals=_known(False, CT["life"], "parallel trial"), biological_feedback=_known(False, PAPER["life"], "behavioral counseling is not biological model feedback"), prospective_policy_evaluation=_known(True, CT["life"], "prospective randomized policy")),
    measurements=[_measurement("major_mobility_disability", "realized_primary_endpoint", _known(1635, PAPER["life"], "1635 sedentary men and women"), _unknown("Event testing is longitudinal and censoring-specific.", [PAPER["life"]], {PAPER["life"]: "400-m walk outcome Methods"}), _known(1, CT["life"], "major mobility disability endpoint"), _unknown("Censoring and visit attendance require participant-level data.", [PAPER["life"]], {PAPER["life"]: "Results"}))],
    classes=dict(exact=["major_mobility_disability"], conditional=[], unknown=[]),
    validation=dict(state="randomized_primary_estimand_reported", reason="This is causal policy evidence, not state reconstruction validation."),
    access=dict(state="application_managed_biobank", source_ids=[PAPER["life"]], reason="Reuse requires the LIFE/NIA biobank process."),
    open_gates=["visit_level_functional_schedule", "biospecimen_module_denominators", "crossmodal_jointness", "information_matrices"],
)


_add(
    "mitoimmune-urolithin-a",
    name="MitoImmune urolithin A trial",
    evaluation_mode="realized_randomized_mechanistic_trial",
    lifecycle="completed_primary_publication",
    source_ids=[CT["mito"], PAPER["mito"]],
    population={"randomized": _known(50, PAPER["mito"], "Methods: n=50 randomized 1:1"), "high_compliance": _known(49, PAPER["mito"], "49 participants reported >90% compliance")},
    timeline={"intervention_duration_days": _known(28, PAPER["mito"], "total study duration was 28 days")},
    design=dict(policy_arms=_known(2, CT["mito"], "/protocolSection/armsInterventionsModule/armGroups"), randomized=_known(True, CT["mito"], "/protocolSection/designModule/designInfo/allocation"), control=_known(True, CT["mito"], "placebo arm"), operators=_known(1, CT["mito"], "urolithin A"), contrasts=_known(1, PAPER["mito"], "UA versus placebo"), adaptive=_known(False, CT["mito"], "parallel fixed assignment"), within_policy=_known(False, CT["mito"], "no randomized component adaptation")),
    personalization=dict(individual_state_models=_known(False, PAPER["mito"], "population-level mechanistic analysis"), adaptive_decisions=_known(False, CT["mito"], "fixed assignment"), randomized_component_personalization=_known(False, CT["mito"], "no personalized component"), within_person_counterfactuals=_known(False, CT["mito"], "parallel trial"), biological_feedback=_known(False, PAPER["mito"], "no feedback policy"), prospective_policy_evaluation=_known(True, CT["mito"], "prospective randomized UA policy")),
    measurements=[
        _measurement("immune_cell_phenotype_and_metabolism", "realized_primary", _known(50, PAPER["mito"], "no participant excluded from final analysis"), _known(2, PAPER["mito"], "baseline and day 28"), _unknown("Flow-cytometry and metabolic target inventory is not one frozen scalar count.", [PAPER["mito"]], {PAPER["mito"]: "Methods"}), _known(50, PAPER["mito"], "primary endpoint samples retained", value_semantics="analysis_participants")),
        _measurement("single_cell_rna", "realized_exploratory_subset", _known(5, PAPER["mito"], "scRNA-seq from five participants before and after both interventions"), _known(2, PAPER["mito"], "before and day 28"), _known(231079, PAPER["mito"], "231,079 cells after QC", unit="cells_not_features"), _unknown("Five participants are an exploratory response-selected subset after unblinding.", [PAPER["mito"]], {PAPER["mito"]: "scRNA Methods/statistics"})),
    ],
    classes=dict(exact=["immune_cell_phenotype_and_metabolism", "single_cell_rna"], conditional=[], unknown=[]),
    validation=dict(state="exploratory_subset_no_external_validation", reason="scRNA subset was selected after unblinding; no held-cohort validation."),
    access=dict(state="publication_plus_bioproject", source_ids=[PAPER["mito"]], reason="Paper routes sequencing data; participant-level full matrix availability is source-specific."),
    open_gates=["full_flow_target_inventory", "assay_specific_missingness", "scRNA_subset_selection_boundary", "joint_event_information_matrices"],
)


_add(
    "motrpac-human-pre-suspension-expanded",
    name="MoTrPAC human pre-suspension cohort",
    evaluation_mode="realized_randomized_acute_multiomic_trial",
    lifecycle="completed_pre_suspension_public_resource_full_trial_separate",
    source_ids=[CT["motrpac"], PAPER["motrpac"]],
    population={"registry_full_program": _known(1837, CT["motrpac"], "/protocolSection/designModule/enrollmentInfo/count"), "pre_suspension_randomized": _known(206, PAPER["motrpac"], "report presents 206 randomized participants"), "acute_assayed": _known(175, PAPER["motrpac"], "175 with at least one biospecimen and molecular assay")},
    timeline={"training_duration_days": _known(84, CT["motrpac"], "Baseline; Week 12", derivation="12*7"), "acute_bout_duration_days": _known(1, PAPER["motrpac"], "baseline acute exercise test", value_semantics="acute_test_day")},
    design=dict(policy_arms=_known(3, PAPER["motrpac"], "EE, RE, CON groups in pre-suspension cohort"), randomized=_known(True, PAPER["motrpac"], "randomized approximate 8:8:3"), control=_known(True, PAPER["motrpac"], "non-exercise control"), operators=_known(2, PAPER["motrpac"], "endurance and resistance exercise"), contrasts=_known(2, PAPER["motrpac"], "EE-versus-control and RE-versus-control acute policies"), adaptive=_known(False, PAPER["motrpac"], "fixed assignment"), within_policy=_known(False, PAPER["motrpac"], "temporal profile randomized for sampling, not treatment adaptation")),
    personalization=dict(individual_state_models=_known(False, PAPER["motrpac"], "group-level molecular map"), adaptive_decisions=_known(False, PAPER["motrpac"], "fixed assignment"), randomized_component_personalization=_known(False, PAPER["motrpac"], "no personalized intervention components"), within_person_counterfactuals=_known(False, PAPER["motrpac"], "parallel trial"), biological_feedback=_known(False, PAPER["motrpac"], "no prospective biological feedback"), prospective_policy_evaluation=_known(True, PAPER["motrpac"], "randomized acute exercise policies")),
    measurements=[
        _measurement("multi_tissue_multiomic_acute", "realized_publication", _known(175, PAPER["motrpac"], "N=175 analyzed"), _unknown("Timepoints vary by tissue, group, and randomized temporal profile.", [PAPER["motrpac"]], {PAPER["motrpac"]: "biospecimen collection Methods"}), _known(3, PAPER["motrpac"], "blood, skeletal muscle, adipose", unit="tissues"), _unknown("Assay coverage varies; Table S1 is required for exact jointness.", [PAPER["motrpac"]], {PAPER["motrpac"]: "Figure S1B and Table S1"})),
        _measurement("whole_genome_sequence", "realized_publication", _known(174, PAPER["motrpac"], "174 of 175 had WGS"), _known(1, PAPER["motrpac"], "per-participant genome"), _known(1, PAPER["motrpac"], "30x WGS assay family"), _unknown("One missing WGS is explicit; jointness with every acute assay is not.", [PAPER["motrpac"]], {PAPER["motrpac"]: "WGS Methods"})),
    ],
    classes=dict(exact=["multi_tissue_multiomic_acute", "whole_genome_sequence"], conditional=[], unknown=[]),
    validation=dict(state="randomized_acute_map_no_held_person_reconstruction", reason="Randomized control supports acute contrasts; no held-person full-state reconstruction benchmark is reported."),
    access=dict(state="public_datahub", source_ids=[PAPER["motrpac"]], reason="Paper routes data and reproducible analysis packages through MoTrPAC resources."),
    open_gates=["table_s1_assay_event_coverage", "exact_cross_tissue_jointness", "full_trial_vs_pre_suspension_lane_separation", "noise_covariances_and_prior"],
)


_add(
    "pearl-rapamycin",
    name="PEARL rapamycin trial",
    evaluation_mode="realized_randomized_trial",
    lifecycle="completed_primary_publication",
    source_ids=[CT["pearl"], PAPER["pearl"]],
    population={"registry_enrollment": _known(129, CT["pearl"], "/protocolSection/designModule/enrollmentInfo/count"), "completers_analyzed": _known(114, PAPER["pearl"], "114 completed and included")},
    timeline={"intervention_duration_days": _known(336, PAPER["pearl"], "48 weeks", derivation="48*7")},
    design=dict(policy_arms=_known(3, CT["pearl"], "/protocolSection/armsInterventionsModule/armGroups"), randomized=_known(True, CT["pearl"], "/protocolSection/designModule/designInfo/allocation"), control=_known(True, CT["pearl"], "placebo arm"), operators=_known(1, CT["pearl"], "rapamycin at two doses"), contrasts=_known(2, PAPER["pearl"], "5mg and 10mg each versus placebo", value_semantics="dose_policy_contrasts"), adaptive=_known(False, CT["pearl"], "parallel fixed assignment"), within_policy=_known(False, CT["pearl"], "no adaptive components")),
    personalization=dict(individual_state_models=_known(False, PAPER["pearl"], "population trial"), adaptive_decisions=_known(False, CT["pearl"], "fixed dose"), randomized_component_personalization=_known(False, CT["pearl"], "dose randomized, not personalized"), within_person_counterfactuals=_known(False, CT["pearl"], "parallel trial"), biological_feedback=_known(False, PAPER["pearl"], "no feedback policy"), prospective_policy_evaluation=_known(True, CT["pearl"], "prospective randomized dose policies")),
    measurements=[
        _measurement("core_clinical_dxa_surveys", "realized_completers", _known(114, PAPER["pearl"], "completers included"), _known(3, PAPER["pearl"], "baseline, 24 weeks, 48 weeks"), _known(3, PAPER["pearl"], "blood, DXA, SF-36/WOMAC families", unit="module_families"), _unknown("Outcome-level denominators vary.", [PAPER["pearl"]], {PAPER["pearl"]: "Results tables"})),
        _measurement("epigenetic_age_subset", "realized_subset", _known(24, PAPER["pearl"], "epigenetic aging analysis n=24"), _known(2, PAPER["pearl"], "baseline and 48 weeks"), _known(1, PAPER["pearl"], "TruAge assay family"), _unknown("Subset selection and paired completeness are not separately reported.", [PAPER["pearl"]], {PAPER["pearl"]: "subset paragraph"})),
        _measurement("gut_microbiome_subset", "realized_subset", _known(81, PAPER["pearl"], "gut microbiome analysis n=81"), _known(2, PAPER["pearl"], "baseline and 48 weeks"), _known(1, PAPER["pearl"], "Thorne Gut Health assay family"), _unknown("Subset selection and paired completeness are not separately reported.", [PAPER["pearl"]], {PAPER["pearl"]: "subset paragraph"})),
    ],
    classes=dict(exact=["core_clinical_dxa_surveys", "epigenetic_age_subset", "gut_microbiome_subset"], conditional=[], unknown=[]),
    validation=dict(state="no_external_validation", reason="Exploratory subgroup and omics findings are not externally validated."),
    access=dict(state="publication_aggregate", source_ids=[PAPER["pearl"]], reason="Public participant-level matrices are not established in the preserved sources."),
    open_gates=["randomized_arm_denominators", "subset_selection_receipts", "joint_participant_event_graph", "formulation_bioavailability_estimand_boundary", "external_validation"],
)


_add(
    "sheba-sharp",
    name="Sheba Healthspan Research Population trial",
    evaluation_mode="registered_protocol_design",
    lifecycle="recruiting_planned_not_realized",
    source_ids=[CT["sharp"]],
    population={"planned_enrollment": _known(1500, CT["sharp"], "/protocolSection/designModule/enrollmentInfo", value_semantics="estimated")},
    timeline={"planned_primary_endpoint_days": _known(365, CT["sharp"], "primary outcome timeFrame 12 months", derivation="1*365", value_semantics="protocol_year_converted_to_days")},
    design=dict(policy_arms=_known(2, CT["sharp"], "/protocolSection/armsInterventionsModule/armGroups"), randomized=_known(True, CT["sharp"], "/protocolSection/designModule/designInfo/allocation"), control=_known(True, CT["sharp"], "control group"), operators=_known(1, CT["sharp"], "personalized healthspan protocol policy"), contrasts=_known(1, CT["sharp"], "personalized protocol versus control"), adaptive=_unknown("The registry states personalized recommendations but not a frozen adaptive reassignment rule.", [CT["sharp"]], {CT["sharp"]: "/protocolSection/armsInterventionsModule"}), within_policy=_known(False, CT["sharp"], "no randomized within-policy components in registry")),
    personalization=dict(individual_state_models=_known(True, CT["sharp"], "personalized recommendation program", evidence_scope="planned_protocol"), adaptive_decisions=_unknown("Recommendation updating rule is not specified.", [CT["sharp"]], {CT["sharp"]: "/protocolSection/armsInterventionsModule/armGroups/0/description"}), randomized_component_personalization=_known(False, CT["sharp"], "personalized components not independently randomized"), within_person_counterfactuals=_known(False, CT["sharp"], "group/crossover design is not randomized N-of-1"), biological_feedback=_known(True, CT["sharp"], "recommendations based on assessment results", evidence_scope="planned_protocol"), prospective_policy_evaluation=_known(True, CT["sharp"], "randomized personalized-policy comparison", evidence_scope="planned_protocol")),
    measurements=[
        _measurement("epigenetic_age", "planned_registry", _known(1500, CT["sharp"], "planned cohort", value_semantics="planned_maximum_not_assay_denominator"), _known(2, CT["sharp"], "baseline and 12 months"), _known(1, CT["sharp"], "DNA methylation aging clocks", unit="module_family"), _unknown("Planned maximum is not expected or realized completeness.", [CT["sharp"]], {CT["sharp"]: "/protocolSection/outcomesModule/primaryOutcomes"})),
        _measurement("healthspan_assessment_battery", "planned_registry", _known(1500, CT["sharp"], "planned cohort", value_semantics="planned_maximum"), _unknown("Exact assessment schedule is not frozen in the registry extract.", [CT["sharp"]], {CT["sharp"]: "/protocolSection/outcomesModule"}), _known(10, CT["sharp"], "ten named assessment domains", unit="domains"), _unknown("Planned battery is not realized completeness.", [CT["sharp"]], {CT["sharp"]: "/protocolSection/armsInterventionsModule/armGroups/0/description"})),
    ],
    classes=dict(exact=[], conditional=["epigenetic_age", "healthspan_assessment_battery"], unknown=[]),
    validation=dict(state="not_yet_eligible", reason="Registered design has no realized held-out evidence."),
    access=dict(state="registry_only", source_ids=[CT["sharp"]], reason="No realized participant-level dataset is asserted."),
    open_gates=["final_protocol_and_sap", "adaptive_policy_specification", "realized_denominators", "assay_platform_inventory", "participant_event_graph"],
)


_add(
    "triim",
    name="TRIIM",
    evaluation_mode="realized_single_arm_pilot",
    lifecycle="completed_exploratory_trial",
    source_ids=[PAPER["triim"]],
    population={"enrolled": _known(10, PAPER["triim"], "trial cohort description"), "analyzed": _known(9, PAPER["triim"], "7 of 9 volunteers and longitudinal analyses")},
    timeline={"intervention_duration_days": _known(365, PAPER["triim"], "months 0-12", derivation="1*365"), "post_intervention_followup_days": _known(180, PAPER["triim"], "month 18 follow-up after month 12", derivation="6*30", value_semantics="nominal_months_converted_to_days")},
    design=dict(policy_arms=_known(1, PAPER["triim"], "single-arm pilot"), randomized=_known(False, PAPER["triim"], "not randomized"), control=_known(False, PAPER["triim"], "no concurrent control"), operators=_known(3, PAPER["triim"], "growth hormone, DHEA, metformin combination components"), contrasts=_known(0, PAPER["triim"], "no assigned comparator"), adaptive=_known(True, PAPER["triim"], "dose adjustments for insulin normalization", evidence_scope="clinical_titration_not_randomized"), within_policy=_known(False, PAPER["triim"], "titration was not randomized")),
    personalization=dict(individual_state_models=_known(False, PAPER["triim"], "no individual state model"), adaptive_decisions=_known(True, PAPER["triim"], "participant dose adjustment", evidence_scope="clinical_titration"), randomized_component_personalization=_known(False, PAPER["triim"], "components not randomized"), within_person_counterfactuals=_known(False, PAPER["triim"], "single arm"), biological_feedback=_known(True, PAPER["triim"], "insulin monitored for dose adjustment"), prospective_policy_evaluation=_known(False, PAPER["triim"], "no comparator policy")),
    measurements=[
        _measurement("dna_methylation", "realized_publication", _known(9, PAPER["triim"], "analysis volunteers"), _known(4, PAPER["triim"], "months 0, 9, 12, 18", unit="reported_longitudinal_timepoints"), _known(866836, PAPER["triim"], "EPIC 866,836 CpG sites"), _unknown("Exact participant by timepoint completeness is not stated as a matrix.", [PAPER["triim"]], {PAPER["triim"]: "DNAm Methods"})),
        _measurement("thymic_mri_and_cytof", "realized_publication", _known(9, PAPER["triim"], "analysis volunteers"), _known(3, PAPER["triim"], "months 0, 9, 12 core treatment timepoints", unit="core_timepoints"), _known(2, PAPER["triim"], "MRI and CyTOF module families"), _unknown("Exact joint rows and post-treatment coverage are not frozen.", [PAPER["triim"]], {PAPER["triim"]: "MRI/CyTOF results"})),
    ],
    classes=dict(exact=["dna_methylation", "thymic_mri_and_cytof"], conditional=[], unknown=[]),
    validation=dict(state="uncontrolled_exploratory", reason="No randomized or concurrent control and n=9 analysis; no external validation."),
    access=dict(state="publication_aggregate", source_ids=[PAPER["triim"]], reason="Participant-level matrices are not established in preserved sources."),
    open_gates=["enrollment_analysis_reconciliation", "concurrent_control", "participant_event_jointness", "multiplicity_control", "external_replication"],
)


_add(
    "zoe-method",
    name="ZOE METHOD",
    evaluation_mode="realized_randomized_personalized_policy_trial",
    lifecycle="completed_primary_publication",
    source_ids=[CT["zoe"], PAPER["zoe"]],
    population={"randomized": _known(347, PAPER["zoe"], "abstract n=347"), "personalized_arm": _known(177, PAPER["zoe"], "abstract PDP n=177"), "control_arm": _known(170, PAPER["zoe"], "abstract control n=170")},
    timeline={"intervention_duration_days": _known(126, PAPER["zoe"], "18-week app-based program", derivation="18*7")},
    design=dict(policy_arms=_known(2, CT["zoe"], "/protocolSection/armsInterventionsModule/armGroups"), randomized=_known(True, CT["zoe"], "/protocolSection/designModule/designInfo/allocation"), control=_known(True, CT["zoe"], "generalized nutrition concurrent comparator"), operators=_known(1, CT["zoe"], "personalized nutrition policy"), contrasts=_known(1, PAPER["zoe"], "PDP versus generalized advice"), adaptive=_known(False, PAPER["zoe"], "no randomized reassignment reported"), within_policy=_known(False, PAPER["zoe"], "personalized food scores are not randomized components")),
    personalization=dict(individual_state_models=_known(True, PAPER["zoe"], "food scores use individual responses, microbiome, and history"), adaptive_decisions=_known(False, PAPER["zoe"], "no sequential reassignment"), randomized_component_personalization=_known(False, PAPER["zoe"], "personalization components not independently randomized"), within_person_counterfactuals=_known(False, PAPER["zoe"], "parallel policy trial"), biological_feedback=_known(True, PAPER["zoe"], "app delivers personalized food scores"), prospective_policy_evaluation=_known(True, PAPER["zoe"], "randomized personalized versus generalized policy")),
    measurements=[
        _measurement("cardiometabolic_endpoints", "realized_itt", _known(347, PAPER["zoe"], "ITT n=347"), _known(2, PAPER["zoe"], "baseline and 18 weeks", unit="primary_endpoint_timepoints"), _known(2, PAPER["zoe"], "LDL cholesterol and triglycerides", unit="primary_endpoints"), _unknown("Outcome-specific data availability differs.", [PAPER["zoe"]], {PAPER["zoe"]: "Results"})),
        _measurement("gut_microbiome", "realized_subset", _known(230, PAPER["zoe"], "118 control plus 112 PDP", derivation="118+112"), _known(3, PAPER["zoe"], "baseline, week 12, week 18"), _known(1, PAPER["zoe"], "gut microbiome assay family"), _known(230, PAPER["zoe"], "microbiome figure denominator", value_semantics="participants_in_reported_microbiome_analysis")),
    ],
    classes=dict(exact=["cardiometabolic_endpoints", "gut_microbiome"], conditional=[], unknown=[]),
    validation=dict(state="randomized_policy_evaluation", reason="The personalized policy is prospectively compared; no held-cohort general biological reconstruction claim is made."),
    access=dict(state="controlled_on_request", source_ids=[PAPER["zoe"]], reason="Paper data-availability terms govern participant-level access."),
    open_gates=["complete_outcome_denominator_table", "personalization_algorithm_version", "joint_microbiome_clinical_event_graph", "component_identifiability", "external_policy_replication"],
)


ANI_COORDINATES = {
    "ani-xprize-finals-200": ("planned_enrollment", "intervention_duration_days", "policy_arms", "randomized_policy_assignment", "active_concurrent_comparator", "deployed_operator_families", "causally_identifiable_policy_contrasts", "adaptive_reassignment", "within_policy_adaptation_randomized"),
    "ani-elite-sheba": ("randomized_itt", "intervention_duration_days", "active_arms", "randomized_assignment", "concurrent_control", "deployed_operator_families", "causally_identifiable_operator_contrasts", "repeated_assignments", None),
    "ani-food4mood": ("planned_enrollment", "total_duration_days", "arms", "randomized_assignment", "concurrent_control", "arm_to_operator_map", None, None, None),
    "ani-oh-my-gut": ("enrolled_or_started", "baseline_to_final_followup_days", "arms", "randomized_assignment", "placebo_concurrent_control", "active_operator_families", None, None, None),
    "ani-geef": ("randomized", "total_followup_days", "arms", "randomized_assignment", "concurrent_control", "operator_families", None, "repeated_assignments", None),
}
ANI_ORDER = list(ANI_COORDINATES)
COORDINATE_COLUMNS = (
    "study_id,projection_lane,population_value,population_semantics,population_state,"
    "duration_days,duration_semantics,duration_state,policy_arms,randomized_policy,"
    "concurrent_control,deployed_operator_families,identifiable_policy_contrasts,"
    "adaptive_reassignment,within_policy_randomized,known_projected_measurement_modules,"
    "conditional_measurement_modules,unknown_measurement_modules,open_gate_count,"
    "source_projection_sha256"
).split(",")


def _authority(source_id: str) -> dict[str, Any]:
    source = SOURCES[source_id]
    path = ROOT / source["snapshot"]
    if not path.is_file():
        raise RuntimeError(f"missing source snapshot: {path}")
    return {
        "source_id": source_id,
        "path": source["snapshot"],
        "url": source["url"],
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
        "hash_scope": "exact_local_response_body_snapshot",
        "evidence_class": source["evidence_class"],
        "locators": source["locators"],
    }


def _projection(study_id: str, spec: dict[str, Any]) -> dict[str, Any]:
    design = spec["design"]
    open_gates = list(spec["open_gates"])
    projection = {
        "schema_version": "ani.source_projection.v2",
        "projection_id": f"{study_id}.source-projection.v2",
        "study_id": study_id,
        "name": spec["name"],
        "projection_status": "candidate_not_scored",
        "evaluation_mode": spec["evaluation_mode"],
        "lifecycle": spec["lifecycle"],
        "authorities": [_authority(source_id) for source_id in spec["source_ids"]],
        "population": spec["population"],
        "timeline": spec["timeline"],
        "intervention_design": {
            "policy_arms": design["policy_arms"],
            "randomized_policy_assignment": design["randomized"],
            "active_concurrent_comparator": design["control"],
            "deployed_operator_families": design["operators"],
            "causally_identifiable_policy_contrasts": design["contrasts"],
            "adaptive_reassignment": design["adaptive"],
            "within_policy_adaptation_randomized": design["within_policy"],
        },
        "personalization": spec["personalization"],
        "measurements": spec["measurements"],
        "participant_event_schedule": {
            "state": "partially_projected",
            "semantics": "measurement rows preserve exact public schedules; no unreported jointness is inferred",
        },
        "crossmodal_links": [],
        "measurement_module_classes": spec["classes"],
        "validation": spec["validation"],
        "access": spec["access"],
        "open_gates": open_gates,
        "field_provenance": {
            "receipt_contract": FIELD_RECEIPT_CONTRACT,
            "known_fact_policy": (
                "A field remains state=known only when every declared source binding "
                "is machine-resolved by a receipted executable derivation."
            ),
            "nonmechanical_fact_policy": (
                "Curated, manual, unresolved, or otherwise non-executable candidate "
                f"values are removed and typed unknown with reason_code={DOWNGRADE_REASON_CODE}."
            ),
            "mechanical_claim_scope": (
                "Only fields whose receipt binds an executable source extractor are "
                "mechanically extracted."
            ),
        },
        "source_coordinate_contract": {
            "contract": SOURCE_COORDINATE_CONTRACT,
            "coordinate_basis": "source_bound_projection_only",
            "overall_scalar": None,
            "public_rank_allowed": False,
            "families": {
                family_id: {
                    "evidence_state": "unknown",
                    "coordinate_state": "not_scoreable",
                    "coordinates": None,
                    "reason": "source_complete_protocol_capacity_geometry_not_available",
                    "open_gate_ids": open_gates,
                }
                for family_id in FAMILY_IDS
            },
        },
    }
    return projection


def _reclassify_measurement_modules(projection: dict[str, Any]) -> None:
    exact: list[str] = []
    conditional: list[str] = []
    unknown: list[str] = []
    for measurement in projection["measurements"]:
        module_id = measurement["id"]
        states = [
            measurement[key].get("state")
            for key in ("participants", "observation_events", "targets", "completeness")
        ]
        if all(state == "known" for state in states):
            exact.append(module_id)
        elif any(state == "known" for state in states):
            conditional.append(module_id)
        else:
            unknown.append(module_id)
    projection["measurement_module_classes"] = {
        "exact": exact,
        "conditional": conditional,
        "unknown": unknown,
        "classification_semantics": (
            "exact=all four public module facts machine-resolved; conditional=at least "
            "one but not all machine-resolved; unknown=no machine-resolved module fact"
        ),
    }


def _fact_value(fact: dict[str, Any] | None) -> str:
    if fact is None or fact.get("state") == "unknown":
        return ""
    value = fact["value"]
    return str(value).lower() if isinstance(value, bool) else str(value)


def _first_fact(section: dict[str, Any], preferred: list[str]) -> tuple[str, dict[str, Any]]:
    for key in preferred:
        if key in section:
            return key, section[key]
    key = next(iter(section))
    return key, section[key]


def _external_coordinate_row(projection: dict[str, Any], sha256: str) -> dict[str, str]:
    population_name, population = _first_fact(
        projection["population"],
        ["randomized", "cohort_enrollment", "combined_profiled", "profiled_participants", "planned_enrollment", "released_participants_lower_bound", "registry_enrollment", "registry_full_program", "enrolled"],
    )
    duration_candidates = [
        key for key in ("intervention_duration_days", "protocol_duration_days", "training_duration_days", "planned_primary_endpoint_days", "median_observation_span_days")
        if key in projection["timeline"]
    ]
    if duration_candidates:
        duration_name = duration_candidates[0]
        duration = projection["timeline"][duration_name]
    else:
        duration_name = next(iter(projection["timeline"]))
        duration = projection["timeline"][duration_name]
        if not duration_name.endswith("_days"):
            duration = {"state": "unknown"}
    design = projection["intervention_design"]
    classes = projection["measurement_module_classes"]
    return {
        "study_id": projection["study_id"],
        "projection_lane": projection["evaluation_mode"],
        "population_value": _fact_value(population),
        "population_semantics": population_name,
        "population_state": population["state"],
        "duration_days": _fact_value(duration),
        "duration_semantics": duration_name,
        "duration_state": duration.get("state", "unknown"),
        "policy_arms": _fact_value(design["policy_arms"]),
        "randomized_policy": _fact_value(design["randomized_policy_assignment"]),
        "concurrent_control": _fact_value(design["active_concurrent_comparator"]),
        "deployed_operator_families": _fact_value(design["deployed_operator_families"]),
        "identifiable_policy_contrasts": _fact_value(design["causally_identifiable_policy_contrasts"]),
        "adaptive_reassignment": _fact_value(design["adaptive_reassignment"]),
        "within_policy_randomized": _fact_value(design["within_policy_adaptation_randomized"]),
        "known_projected_measurement_modules": str(len(classes["exact"])),
        "conditional_measurement_modules": str(len(classes["conditional"])),
        "unknown_measurement_modules": str(len(classes["unknown"])),
        "open_gate_count": str(len(projection["open_gates"])),
        "source_projection_sha256": sha256,
    }


def _ani_coordinate_row(projection: dict[str, Any], sha256: str) -> dict[str, str]:
    names = ANI_COORDINATES[projection["study_id"]]
    pop_name, duration_name, *design_names = names
    design = projection["intervention_design"]
    columns = ("policy_arms", "randomized_policy", "concurrent_control", "deployed_operator_families", "identifiable_policy_contrasts", "adaptive_reassignment", "within_policy_randomized")
    row = {
        "study_id": projection["study_id"], "projection_lane": projection["evaluation_mode"],
        "population_value": _fact_value(projection["population"][pop_name]), "population_semantics": pop_name, "population_state": projection["population"][pop_name]["state"],
        "duration_days": _fact_value(projection["timeline"][duration_name]), "duration_semantics": duration_name, "duration_state": projection["timeline"][duration_name]["state"],
    }
    for column, name in zip(columns, design_names, strict=True):
        row[column] = _fact_value(None if name is None else design[name])
    classes = projection["measurement_module_classes"]
    row.update(known_projected_measurement_modules=str(len(classes["exact"])), conditional_measurement_modules=str(len(classes["conditional"])), unknown_measurement_modules=str(len(classes["unknown"])), open_gate_count=str(len(projection["open_gates"])), source_projection_sha256=sha256)
    return row


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def build() -> None:
    source_index = {
        source_id: _authority(source_id)
        for source_id in sorted(SOURCES)
    }
    raw_source_cache = {
        source_id: (ROOT / source["path"]).read_bytes()
        for source_id, source in source_index.items()
    }
    projection_rows = []
    for study_id in sorted(STUDIES):
        spec = STUDIES[study_id]
        projection, machine_policy = enforce_machine_resolved_known_facts(
            projection=_projection(study_id, spec),
            source_index=source_index,
            raw_source_cache=raw_source_cache,
        )
        _reclassify_measurement_modules(projection)
        projection["field_provenance"].update(machine_policy)
        projection_path = PROJECTION_ROOT / f"{study_id}.json"
        _write_json(projection_path, projection)
        projection_rows.append({
            "study_id": study_id,
            "path": projection_path.relative_to(ROOT).as_posix(),
            "sha256": _sha256(projection_path),
            "evaluation_mode": spec["evaluation_mode"],
            "source_coordinate_contract": SOURCE_COORDINATE_CONTRACT,
            "disposition": "source_bound_six_family_coordinates_typed_not_scoreable",
        })

    source_rows = []
    for source_id in sorted(SOURCES):
        authority = _authority(source_id)
        source_rows.append(authority)
    _write_json(ACQUISITION_LEDGER, {
        "schema_version": "ani.external_source_acquisition_ledger.v2",
        "retrieved_date": "2026-07-12",
        "status": "exact_local_response_body_snapshots",
        "sources": source_rows,
    })
    ledger_path = PROJECTION_ROOT / "SOURCE_PROJECTION_LEDGER.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ani_rows = [row for row in ledger["projections"] if row["study_id"] in ANI_ORDER]
    ledger["projections"] = ani_rows + projection_rows
    ledger["external_source_acquisition_ledger"] = {
        "path": ACQUISITION_LEDGER.relative_to(ROOT).as_posix(),
        "sha256": _sha256(ACQUISITION_LEDGER),
    }
    ledger.pop("external_corpus_coverage", None)
    ledger["authority_hashes"] = [
        row for row in ledger.get("authority_hashes", [])
        if not str(row["path"]).startswith("data/source_projections/v2/sources/")
    ] + [{"path": row["path"], "sha256": row["sha256"]} for row in source_rows]

    all_projections: list[tuple[dict[str, Any], str]] = []
    for study_id in ANI_ORDER:
        path = PROJECTION_ROOT / f"{study_id}.json"
        all_projections.append((json.loads(path.read_text(encoding="utf-8")), _sha256(path)))
    for row in projection_rows:
        path = ROOT / row["path"]
        all_projections.append((json.loads(path.read_text(encoding="utf-8")), row["sha256"]))
    coordinate_path = PROJECTION_ROOT / "SOURCE_COORDINATE_TABLE.csv"
    with coordinate_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COORDINATE_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for projection, sha in all_projections:
            writer.writerow(_ani_coordinate_row(projection, sha) if projection["study_id"] in ANI_COORDINATES else _external_coordinate_row(projection, sha))
    ledger["coordinate_table"]["sha256"] = _sha256(coordinate_path)
    ledger["ledger_id"] = "anibench-source-projections-v2-2026-07-12-external-corpus"
    _write_json(ledger_path, ledger)

    field_receipt = build_field_provenance_receipt(
        root=ROOT,
        projection_ids=tuple(sorted(STUDIES)),
        acquisition_ledger=ACQUISITION_LEDGER,
        coordinate_table=PUBLIC_COORDINATE_TABLE,
    )
    _write_json(FIELD_RECEIPT, field_receipt)


def check() -> None:
    expected: dict[Path, bytes] = {}
    # Generate into the checkout, capture deterministic bytes, then compare to a
    # second generation.  This detects accidental nondeterminism and missing files.
    build()
    paths = [PROJECTION_ROOT / f"{study_id}.json" for study_id in STUDIES]
    paths += [
        ACQUISITION_LEDGER,
        PROJECTION_ROOT / "SOURCE_COORDINATE_TABLE.csv",
        PROJECTION_ROOT / "SOURCE_PROJECTION_LEDGER.json",
        PUBLIC_COORDINATE_TABLE,
        FIELD_RECEIPT,
    ]
    expected = {path: path.read_bytes() for path in paths}
    build()
    changed = [path for path, body in expected.items() if path.read_bytes() != body]
    if changed:
        raise SystemExit("nondeterministic external corpus outputs: " + ", ".join(map(str, changed)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    check() if args.check else build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
