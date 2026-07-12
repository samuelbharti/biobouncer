# Sources cookbook

biogate checks 39 sources. Each row below gives a valid example id, the
[checking modes](guide.md#the-checking-modes) it supports, and whether it is
species-aware. To check an id, pass the source key as `source_db`. The call is
the same for every source:

```python
import biogate as bg

bg.is_valid_id("MONDO:0005148", source_db="mondo")
# True
```

The full table is also available in code, so you never have to guess a key or an
example:

```python
for row in bg.source_info():
    print(row["key"], row["example"], row["modes"])
```

Modes: `pattern` checks the shape offline, `cache` checks existence against a
pinned snapshot, and `remote` checks existence against the live source. See the
[guide](guide.md) for details.

## Diseases

| Source | `source_db` | Example | Modes | Species-aware |
|---|---|---|---|---|
| MONDO Disease Ontology. Cross-referenced disease terms from the Monarch Initiative. | `mondo` | `MONDO:0005148` | pattern, cache, remote | no |
| Human Disease Ontology. Human diseases, mapped to other disease vocabularies. | `doid` | `DOID:9352` | pattern, cache, remote | no |
| Experimental Factor Ontology. Diseases, traits, and measurements from the GWAS Catalog and Open Targets. | `efo` | `EFO:0000400` | pattern, cache, remote | no |
| Orphanet. Rare diseases. | `orphanet` | `ORPHA:558` | pattern, remote | no |
| NCI Thesaurus. Cancer and biomedical concepts. | `ncit` | `NCIT:C3224` | pattern, remote | no |

Check any id in the group the same way:

```python
bg.is_valid_id("MONDO:0005148", source_db="mondo")
```

## Phenotypes and traits

| Source | `source_db` | Example | Modes | Species-aware |
|---|---|---|---|---|
| Human Phenotype Ontology. Human phenotypic abnormalities used in clinical genetics. | `hp` | `HP:0001250` | pattern, cache, remote | no |
| Mammalian Phenotype Ontology. Mammalian phenotypes, common in mouse studies. | `mp` | `MP:0001262` | pattern, cache, remote | no |
| Phenotype And Trait Ontology. Qualities and traits, often composed with other ontologies. | `pato` | `PATO:0000001` | pattern, cache, remote | no |

Check any id in the group the same way:

```python
bg.is_valid_id("HP:0001250", source_db="hp")
```

## Anatomy, cells, and tissues

| Source | `source_db` | Example | Modes | Species-aware |
|---|---|---|---|---|
| Uberon. Cross-species anatomy. | `uberon` | `UBERON:0002107` | pattern, cache, remote | no |
| Cell Ontology. Cell types. | `cl` | `CL:0000236` | pattern, cache, remote | no |
| BRENDA Tissue Ontology. Tissues and cell lines from BRENDA. | `bto` | `BTO:0000759` | pattern, cache, remote | no |

Check any id in the group the same way:

```python
bg.is_valid_id("UBERON:0002107", source_db="uberon")
```

## Organisms and taxa

| Source | `source_db` | Example | Modes | Species-aware |
|---|---|---|---|---|
| NCBI Taxonomy. Organisms and other taxa. | `ncbitaxon` | `NCBITaxon:9606` | pattern, remote | no |

Check any id in the group the same way:

```python
bg.is_valid_id("NCBITaxon:9606", source_db="ncbitaxon")
```

## Genes

| Source | `source_db` | Example | Modes | Species-aware |
|---|---|---|---|---|
| HGNC gene symbols. Approved symbols. A withdrawn symbol maps to its successor. | `hgnc` | `TP53` | pattern | no |
| Ensembl. Ensembl gene, transcript, and protein ids. Species-aware. | `ensembl` | `ENSG00000139618` | pattern, remote | yes |
| RefSeq. NCBI RefSeq accessions, with an optional version. | `refseq` | `NM_000546.6` | pattern, remote | no |

Check any id in the group the same way:

```python
bg.is_valid_id("TP53", source_db="hgnc")
```

## Variants

| Source | `source_db` | Example | Modes | Species-aware |
|---|---|---|---|---|
| dbSNP. dbSNP reference SNP ids. | `dbsnp` | `rs7412` | pattern, remote | no |
| HGVS. HGVS sequence variant syntax, such as a coding substitution. | `hgvs` | `NM_004006.2:c.4375C>T` | pattern, remote | no |
| ClinVar. ClinVar variation, record, and submission accessions. | `clinvar` | `VCV000012345` | pattern, remote | no |
| COSMIC. COSMIC somatic mutation ids. | `cosmic` | `COSM476` | pattern | no |

Check any id in the group the same way:

```python
bg.is_valid_id("rs7412", source_db="dbsnp")
```

## Proteins and structures

| Source | `source_db` | Example | Modes | Species-aware |
|---|---|---|---|---|
| UniProt. UniProt protein accessions. Species-aware. | `uniprot` | `P04637` | pattern, remote | yes |
| UniParc. UniParc unique sequence identifiers. | `uniparc` | `UPI0000000001` | pattern, remote | no |
| PDB. Protein Data Bank structures. | `pdb` | `4HHB` | pattern, remote | no |
| Complex Portal. Macromolecular complexes. | `complexportal` | `CPX-2158` | pattern, remote | no |

Check any id in the group the same way:

```python
bg.is_valid_id("P04637", source_db="uniprot")
```

## Protein families and domains

| Source | `source_db` | Example | Modes | Species-aware |
|---|---|---|---|---|
| Pfam. Protein families and domains. | `pfam` | `PF00001` | pattern, remote | no |
| InterPro. Integrated protein families, domains, and sites. | `interpro` | `IPR000001` | pattern, remote | no |
| PROSITE. Protein patterns and profiles. | `prosite` | `PS00001` | pattern, remote | no |

Check any id in the group the same way:

```python
bg.is_valid_id("PF00001", source_db="pfam")
```

## Function, sequence, and enzymes

| Source | `source_db` | Example | Modes | Species-aware |
|---|---|---|---|---|
| Gene Ontology. Gene Ontology terms for function, process, and component. | `go` | `GO:0006915` | pattern, cache, remote | no |
| Sequence Ontology. Sequence Ontology features. | `so` | `SO:0000704` | pattern, cache, remote | no |
| EC number. Enzyme Commission numbers. | `ec` | `1.1.1.1` | pattern | no |
| Evidence and Conclusion Ontology. Evidence types for annotations. | `eco` | `ECO:0000269` | pattern, remote | no |

Check any id in the group the same way:

```python
bg.is_valid_id("GO:0006915", source_db="go")
```

## Chemicals and drugs

| Source | `source_db` | Example | Modes | Species-aware |
|---|---|---|---|---|
| ChEBI. Chemical entities of biological interest. | `chebi` | `CHEBI:15377` | pattern, cache, remote | no |
| ChEMBL. Bioactive molecules. | `chembl` | `CHEMBL25` | pattern, remote | no |
| DrugBank. Drug accessions. | `drugbank` | `DB00001` | pattern | no |
| PharmGKB. Pharmacogenomics accessions. | `pharmgkb` | `PA267` | pattern | no |
| InChIKey. Hashed chemical structure keys. | `inchikey` | `BSYNRYMUTXBXSQ-UHFFFAOYSA-N` | pattern | no |

Check any id in the group the same way:

```python
bg.is_valid_id("CHEBI:15377", source_db="chebi")
```

## Pathways

| Source | `source_db` | Example | Modes | Species-aware |
|---|---|---|---|---|
| Reactome. Reactome pathways, reactions, and entities. | `reactome` | `R-HSA-68886` | pattern, remote | no |
| WikiPathways. Community-curated pathways. | `wikipathways` | `WP554` | pattern, remote | no |

Check any id in the group the same way:

```python
bg.is_valid_id("R-HSA-68886", source_db="reactome")
```

## RNA families

| Source | `source_db` | Example | Modes | Species-aware |
|---|---|---|---|---|
| Rfam. RNA families. | `rfam` | `RF00001` | pattern, remote | no |
| miRBase. Mature microRNAs. | `mirbase` | `MIMAT0000001` | pattern, remote | no |

Check any id in the group the same way:

```python
bg.is_valid_id("RF00001", source_db="rfam")
```
