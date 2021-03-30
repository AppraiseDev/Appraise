# Appraise Evaluation Framework

[![release](https://img.shields.io/github/v/release/AppraiseDev/Appraise?include_prereleases)](https://github.com/AppraiseDev/Appraise/releases)
[![license: BSD](https://img.shields.io/badge/license-BSD-blue.svg)](./LICENSE)

Appraise is an open-source framework for crowd-based annotation tasks, notably
for evaluation of machine translation (MT) outputs. The software is used to run
the yearly human evaluation campaigns for shared tasks at the [WMT Conference on
Machine Translation](http://www.statmt.org/wmt21/) and other events.

Annotation tasks currently supported in Appraise:
* Segment-level direct assessment
* Document-level direct assessments
* Pairwise direct assessment (a.k.a RankME)
* Multimodal MT assessment

## Getting Started

See [INSTALL.md](https://github.com/AppraiseDev/Appraise/blob/master/INSTALL.md)
for a step-by-step instructions on how to install prerequisites and setup
Appraise.

## Usage

See [`Examples/`](Examples/) for simple end-to-end examples for setting up
currently supported annotation tasks and read [how to create your own
campaign](https://github.com/AppraiseDev/Appraise/blob/master/INSTALL.md#creating-a-new-campaign)
in Appraise.

## License

This project is licensed under the [LICENSE](BSD-3-Clause License).

## Citation

If you use Appraise in your research, please cite the following paper:

    @inproceedings{federmann-2018-appraise,
        title = "Appraise Evaluation Framework for Machine Translation",
        author = "Federmann, Christian",
        booktitle = "Proceedings of the 27th International Conference on
            Computational Linguistics: System Demonstrations",
        month = aug,
        year = "2018",
        address = "Santa Fe, New Mexico",
        publisher = "Association for Computational Linguistics",
        url = "https://www.aclweb.org/anthology/C18-2019",
        pages = "86--88"
    }

