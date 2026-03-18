<div align="center">

# Nimbus: A Unified Embodied Synthetic Data Generation Framework

</div>

<div align="center">

[![Paper Nimbus](https://img.shields.io/badge/Paper-Nimbus-red.svg)](https://arxiv.org/abs/2601.21449)
[![Data InternData-A1](https://img.shields.io/badge/Data-InternData--A1-blue?logo=huggingface)](https://huggingface.co/datasets/InternRobotics/InternData-A1)
[![Data InternData-M1](https://img.shields.io/badge/Data-InternData--M1-blue?logo=huggingface)](https://huggingface.co/datasets/InternRobotics/InternData-M1)
[![Data InternData-N1](https://img.shields.io/badge/Data-InternData--N1-blue?logo=huggingface)](https://huggingface.co/datasets/InternRobotics/InternData-N1)
[![Docs](https://img.shields.io/badge/Docs-Online-green.svg)](https://internrobotics.github.io/InternDataEngine-Docs/)

</div>

## 💻 About

Nimbus is a scalable synthetic data generation framework that supports large-scale dataset production for both embodied navigation and manipulation tasks. It already powers the generation and public release of the InternData series([A1](https://huggingface.co/datasets/InternRobotics/InternData-A1)/[N1](https://huggingface.co/datasets/InternRobotics/InternData-N1)/[M1](https://huggingface.co/datasets/InternRobotics/InternData-M1)), and can be integrated into different simulation backends to orchestrate planning, rendering, and storage at scale. For best practices and end-to-end usage examples, please refer to [**InternDataEngine**](https://github.com/InternRobotics/InternDataEngine), which provides a complete stack built on top of Nimbus.

## License and Citation
All the code within this repo are under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Please consider citing our papers if it helps your research.

```BibTeX
@article{he2026nimbus,
  title={Nimbus: A Unified Embodied Synthetic Data Generation Framework},
  author={He, Zeyu and Zhang, Yuchang and Zhou, Yuanzhen and Tao, Miao and Li, Hengjie and Tian, Yang and Zeng, Jia and Wang, Tai and Cai, Wenzhe and Chen, Yilun and others},
  journal={arXiv preprint arXiv:2601.21449},
  year={2026}
}
```