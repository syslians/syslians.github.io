---
title: "VMware + Vagrant + kubeadm + Cilium 트러블슈팅 기록"
date: "2026-07-28T07:22:09.678Z"
categories:
  - "vmware"
  - "vagrant"
  - "k8s"
  - "cillium"
author: "현제 김_7254"
slug: "vmware_vagrant_kubeadm_cilium_트러블슈팅_기록"
---

## Rocky Linux Worker Node 생성부터 Cillium VXLAN Overlay 복구까지

### 1. 개요 

이번 작업의 목표는 컨트롤 플레인으로 운영중이던 우분투 기반 kubernetes Control Plane에 Rocky Linux Worker Node를 새롭게 추가시키는 것이였다.

단순히 kubeadm join만 하면 끝날 줄 알았지만 실제로는 다음과 같은 문제가 연쇚