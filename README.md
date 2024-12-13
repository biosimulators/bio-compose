[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1bVtTmbMLnfFBv44rPwmBFsHvpX7woDWn?usp=sharing)
![Deployment Pipeline](https://github.com/biosimulators/bio-compose/actions/workflows/pipeline.yml/badge.svg)
[![Documentation](https://readthedocs.org/projects/bio-compose/badge/?version=latest)](https://bio-compose.readthedocs.io/en/latest/)

# **BioCompose**: Create, execute, and introspect reproducible composite simulations of dynamic biological systems.
#### __This service utilizes separate containers for REST API management, job processing, and datastorage with MongoDB, ensuring scalable and robust performance.__

## **Documentation**: 

The complete `BioCompose` documentation can be found here: https://bio-compose.readthedocs.io/en/latest/

## **Getting Started**:

### _HIGH-LEVEL `bio_compose` API:_

The primary method of user-facing interaction for this service is done through the use of a high-level "notebook" api called `bio_check`. 
A convenient notebook demonstrating the functionality of this service is hosted on Google Colab and can be accessed by clicking the above "Open In Colab" badge.

Installation of this tooling can be performed using PyPI as such:

```bash
pip install bio-compose
```

#### Alternatively, **the REST API can be accessed via Swagger UI here: [https://biochecknet.biosimulations.org/docs](https://biochecknet.biosimulations.org/docs)**

## Smoldyn to Simularium conversion:

A convienient template notebook for converting the outputs of Smoldyn simulations to Simularium trajectories can be
[found here.](https://colab.research.google.com/drive/17uMMRq3L3KqRIXnezahM6TtOtJYK8Cu6#scrollTo=6n5Wf58hthFm)