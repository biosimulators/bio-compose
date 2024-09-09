Installation
============

To install `bio-compose`, you can use pip:

.. code-block:: bash

   pip install bio-compose

If you are installing from source, clone the repository and use the following commands:

.. code-block:: bash

   git clone https://github.com/biosimulators/bio-compose.git
   cd your_project
   pip install -e .


Verification
============


Running a verification with `bio-compose` can be achieved in a few simple steps.

Running a **OMEX verifications**:

.. code-block:: python

    from bio_compose import verify

    filepath = '/path/to/a/valid/omex/file.omex'
    simulators = ['amici', 'copasi', 'tellurium']

    verification = verify(filepath, simulators)


Running **SBML verifications**:

.. code-block:: python

    from bio_compose import verify

    filepath = '/path/to/a/valid/sbml/file.xml'
    simulators = ['amici', 'copasi', 'tellurium']
    start_time = 0
    duration = 100
    n_steps = 1000

    verification = verify(filepath, start_time, duration, n_steps, simulators)


Simulation Runs
===============

`bio-compose` has a `run_simulation` method that can be used to run either: a Smoldyn simulation **OR** a SBML simulation.

Running a **Smoldyn simulation**:

.. code-block:: python

    from bio_compose import run_simulation

    filepath = '/path/to/a/valid/smoldyn/configuration/txt/file.txt'
    duration = 10
    dt = 0.02
    result = run_simulation(filepath, duration, dt)


Running a **SBML simulation**:

.. code-block:: python

    from bio_compose import run_simulation

    filepath = '/path/to/a/valid/sbml/file.xml'
    simulator = 'copasi'
    start_time = 0
    duration = 100
    n_steps = 1000
    result = run_simulation(filepath, start_time, duration, n_steps, simulator)







