# RFC 104: Enterprise Platform Architecture & Scalability Specs

## 1. Executive Summary
This document specifies the microservices architecture, data streaming pipeline, and caching layer for the core platform. Target system availability is 99.99% uptime with p99 latency under 120ms.

## 2. Infrastructure & Microservices Layout
- **API Gateway**: Traefik v3.0 managing rate limiting, TLS termination, and OAuth2 JWT authentication.
- **Event Streaming**: Apache Kafka 3.6 configured with 3-broker cluster, replication factor of 3, and min.isr set to 2.
- **Primary Database**: PostgreSQL 16 with Read Replicas (PgBouncer connection pooling max 500 connections).
- **Caching Layer**: Redis Enterprise Cluster (v7.2) using LRU eviction policy and 5-minute TTL on hot queries.
- **Orchestration**: Kubernetes v1.29 cluster deployed on AWS EKS across 3 availability zones (`us-east-1a`, `us-east-1b`, `us-east-1c`).

## 3. SLA & Performance Benchmarks
- **Max Throughput**: 45,000 requests per second (RPS) during peak load.
- **Database Failover Time**: Automated failover via Patroni in under 15 seconds.
- **Disaster Recovery (RPO/RTO)**: Recovery Point Objective (RPO) < 1 minute; Recovery Time Objective (RTO) < 15 minutes.
- **Lead Infrastructure Architect**: Marcus Vance (`marcus.vance@company.com`).
