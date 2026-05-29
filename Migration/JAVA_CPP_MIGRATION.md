# Java + C++ Migration Bootstrap

This repository now contains the first implementation slice for the JavaFX plus native C++ migration target.

## Added modules

- `java-shell/`: Java application shell module using Gradle and Java 21.
- `native-core/`: C++ engine module using CMake.

## What is implemented

### Java shell

The Java shell contains the first real contract port from Python:

- `BrainInput`: Java version of the current brain input contract.
- `RouteDecision`: Java version of the current routing decision contract.
- `RoutingConfig`: Java-owned routing thresholds.
- `IntentRouter`: port of the routing semantics from `MAIINNN.Connectors/intent_router.py`.
- `Bootstrap`: minimal entry point for manual smoke testing.
- `IntentRouterTest`: JUnit tests proving the ported routing behavior.

### Native core

The native core contains the first stable facade for the future AI runtime:

- `EngineFacade`: single native entry point instead of scattered JNI calls.
- `BrainInput`: native-side routing input contract.
- `RouteDecision`: native-side routing output contract.

The current native facade implements the same routing semantics as the Java shell. That gives both sides a shared behavioral baseline while the rest of the engine is still pending.

## Why this is the right first slice

The current Python codebase is large, but the routing contract is compact, central, and easy to verify. Porting it first establishes:

1. stable contracts
2. parallel Java and C++ implementations
3. a buildable migration boundary
4. a pattern for porting the next subsystems

## Next implementation targets

1. Port `BrainResult`, `SpinalResult`, and parser contracts into Java.
2. Define the engine facade methods for classification, memory search, graph inference, and actions.
3. Add JNI or RPC bridge code only after the engine facade stops changing.
4. Port the orchestrator flow into Java service classes.

## Build commands

### Java shell

From `java-shell/`:

`gradle test`

or if Gradle wrapper is added later:

`./gradlew test`

### Native core

From `native-core/`:

`cmake -S . -B build`

`cmake --build build`

## Important constraint

This is not a Python interop layer. It is the start of the replacement architecture. Python remains the current runtime only until parity contracts are fully captured and the Java/C++ stack can take over subsystem by subsystem.