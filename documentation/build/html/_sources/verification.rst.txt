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