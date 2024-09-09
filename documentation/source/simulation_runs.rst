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