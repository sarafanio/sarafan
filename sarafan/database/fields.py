from dataclasses import field as dc_field, MISSING


def field(*,
          db_name=None,
          default=MISSING,
          default_factory=MISSING,
          init=True,
          repr=True,
          hash=None,
          compare=True,
          metadata=None):
    return dc_field(
        default=default,
        default_factory=default_factory,
        init=init,
        repr=repr,
        hash=hash,
        compare=compare,
        metadata={
            'db_name': db_name,
        }
    )
