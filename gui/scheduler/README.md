# Generate ProtoBuf files

```bash
python3 -m grpc_tools.protoc  --python_out=. --pyi_out=. --grpc_python_out=. ../../api/proto/solver/v1/solver.proto  --proto_path ../api/proto/
```