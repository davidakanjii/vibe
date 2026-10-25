terraform {
  required_version = ">= 1.6, < 2.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" { region = var.aws_region }

variable "aws_region" {
  type    = string
  default = "eu-west-1"
}
variable "vpc_id" { type = string }
variable "subnet_id" { type = string }
variable "ubuntu_ami_id" {
  type        = string
  description = "Reviewed Ubuntu 24.04 LTS AMI in the selected region; verify its publisher and architecture."
}
variable "key_name" { type = string }
variable "admin_cidr" {
  type        = string
  description = "Administrator public IPv4 address with /32; never use 0.0.0.0/0."
  validation {
    condition     = can(cidrhost(var.admin_cidr, 0)) && endswith(var.admin_cidr, "/32")
    error_message = "Use one administrator IPv4 /32 address."
  }
}
variable "instance_type" {
  type    = string
  default = "t3.medium"
}

resource "aws_security_group" "app" {
  name_prefix = "vibesync-"
  description = "HTTPS web ingress and restricted administrative SSH; audio ingress excluded"
  vpc_id      = var.vpc_id
  ingress {
    from_port = 22
    to_port = 22
    protocol = "tcp"
    cidr_blocks = [var.admin_cidr]
  }
  ingress {
    from_port = 80
    to_port = 80
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port = 443
    to_port = 443
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Project = "VibeSync" }
}

resource "aws_instance" "app" {
  ami                         = var.ubuntu_ami_id
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_id
  key_name                    = var.key_name
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.app.id]
  metadata_options { http_tokens = "required" }
  root_block_device {
    encrypted   = true
    volume_size = 40
    volume_type = "gp3"
  }
  user_data = <<-CLOUDINIT
    #cloud-config
    package_update: true
    packages:
      - docker.io
      - docker-compose-v2
      - git
    runcmd:
      - [systemctl, enable, --now, docker]
  CLOUDINIT
  tags = { Name = "vibesync", Project = "VibeSync" }
}

resource "aws_eip" "app" {
  instance = aws_instance.app.id
  domain   = "vpc"
}
output "public_ip" { value = aws_eip.app.public_ip }
