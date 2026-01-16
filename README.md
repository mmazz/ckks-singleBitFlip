# CKKS Single Bit flip injeccion

We inject single-bit faults at the RNS-limb level, flipping one bit of a uint64_t coefficient of a single CRT component, either in coefficient or NTT domain, at a well-defined pipeline stage (encode, encrypt-c0, encrypt-c1).

campaign_arguments.*
    - Parsea argumentos


campaign_registry.*
  - asigna campaign_id (atomic, inter-proceso)
  - escribe CSV GLOBAL de inicio
  - escribe CSV GLOBAL de finalización
  - SOLO append

campaign_logger.*
  - escribe CSV por campaña (bitflips)
  - thread-safe local
  - NUNCA toca el registry automáticamente

campaign_helper.*
  - parse args
  - crea registry
  - registra inicio
  - arma logger
  - al final registra cierre

Dependancys:
zlib
