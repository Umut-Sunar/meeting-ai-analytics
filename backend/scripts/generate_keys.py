#!/usr/bin/env python3
"""
Generate RSA key pairs for JWT authentication (development only).
"""

import os
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


def generate_jwt_keys(keys_dir: str = "keys") -> None:
    """Generate RSA key pair for JWT signing."""
    
    # Create keys directory
    os.makedirs(keys_dir, exist_ok=True)
    
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    
    # Generate public key
    public_key = private_key.public_key()
    
    # Serialize private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Serialize public key
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    # Write private key
    private_key_path = os.path.join(keys_dir, "jwt.key")
    with open(private_key_path, "wb") as f:
        f.write(private_pem)
    
    # Write public key
    public_key_path = os.path.join(keys_dir, "jwt.pub")
    with open(public_key_path, "wb") as f:
        f.write(public_pem)
    
    print(f"✅ Generated JWT keys:")
    print(f"   Private key: {private_key_path}")
    print(f"   Public key: {public_key_path}")
    print()
    print("⚠️  IMPORTANT: These are development keys only!")
    print("   DO NOT use in production.")
    print("   DO NOT commit to git.")


if __name__ == "__main__":
    generate_jwt_keys()
