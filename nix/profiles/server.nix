{ config, pkgs, lib, ... }:
# Server profile — headless/minimal UI, infrastructure management
# Activated when: night hours, manual switch, or server tools detected
{
  environment.systemPackages = with pkgs; [
    # Infrastructure & containers
    docker docker-compose
    kubectl helm k9s
    terraform ansible

    # Monitoring & logs
    prometheus grafana
    loki promtail
    htop btop iotop nethogs
    lnav  # log navigator

    # Network tools
    nmap wireshark-cli
    tcpdump mtr
    iperf3 netcat-openbsd

    # Database clients
    postgresql mysql80
    redis

    # Web servers
    nginx certbot

    # Security
    fail2ban lynis
    aide  # intrusion detection

    # Remote access
    openssh rsync
    tmux screen
  ];

  # ── Services ────────────────────────────────────────────
  virtualisation.docker = {
    enable = true;
    autoPrune = { enable = true; dates = "weekly"; };
  };

  services = {
    openssh = {
      enable = true;
      settings = {
        PasswordAuthentication = false;
        PermitRootLogin = "no";
        X11Forwarding = false;
      };
    };
    fail2ban.enable = true;
    prometheus.enable = lib.mkDefault false;  # Enable explicitly when needed
    grafana.enable  = lib.mkDefault false;
  };

  # ── Firewall: strict in server mode ─────────────────────
  networking.firewall = {
    enable = true;
    allowedTCPPorts = [ 22 80 443 ];
  };

  # ── CPU: balanced (schedutil) ───────────────────────────
  powerManagement.cpuFreqGovernor = "schedutil";

  # ── Disable GPU & unnecessary desktop services ──────────
  hardware.nvidia.powerManagement.enable = lib.mkForce true;

  # ── Kernel: network & server tuning ─────────────────────
  boot.kernel.sysctl = {
    "net.core.somaxconn"          = 65535;
    "net.ipv4.tcp_max_syn_backlog" = 65535;
    "vm.swappiness"               = 10;
    "fs.file-max"                 = 2097152;
  };

  # ── Disable display manager in pure server mode ─────────
  # services.greetd.enable = lib.mkForce false;
}
