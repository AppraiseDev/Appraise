# Appraise Evaluation Framework

[![release](https://img.shields.io/github/v/release/AppraiseDev/Appraise?include_prereleases)](https://github.com/AppraiseDev/Appraise/releases)
[![license: BSD](https://img.shields.io/badge/license-BSD-blue.svg)](./LICENSE)

Appraise is an open-source framework for crowd-based annotation tasks, notably
for evaluation of machine translation (MT) outputs. The software is used to run
the yearly human evaluation campaigns for shared tasks at the [WMT Conference on
Machine Translation](http://www.statmt.org/wmt21/) and other events.

Annotation tasks currently supported in Appraise:
* Segment-level direct assessment ([DA](https://www.aclweb.org/anthology/W13-2305/))
* Document-level direct assessment
* Pairwise direct assessment (similar to [EASL](https://www.aclweb.org/anthology/P18-1020/) and [RankME](https://www.aclweb.org/anthology/N18-2012/))
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

This project is licensed under the [BSD-3-Clause License](LICENSE).

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

## WMT21 Collaboration with Toloka

For WMT21 we have partnered with Toloka to collect more annotations for the human evaluation of the news translation shared task. We are grateful for their support and look forward to our continued collaboration in the future!

In Toloka's own words:

> The international data labeling platform Toloka collaborated with the WMT team to improve existing machine translation methods. Toloka's crowdsourcing service was integrated with Appraise, an open-source framework for human-based annotation tasks.
>
> To increase the accuracy of machine translation, we need to systematically compare different MT methods to reference data. However, obtaining sufficient reference data can pose a challenge, especially for rare languages. Toloka solved this problem by providing a global crowdsourcing platform with enough annotators to cover all relevant language pairs. At the same time, the integration preserved the labeling processes that were already set up in Appraise without breaking any tasks.
>
> Collaboration between Toloka and Appraise made it possible to get a relevant pool of annotators, provide them with an interface for labeling and getting rewards, and then combine quality control rules from both systems into a mutually reinforcing set for reliable results.

You can learn more about Toloka on their website: https://toloka.ai/
