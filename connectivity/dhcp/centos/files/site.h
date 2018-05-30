/*
 * define config file location in ${S}/includes/site.h
 * still need to take care of installation path (${sysconfdir}/dhcpd.conf)
 *
 * 7/22/2010 - qhe
 */

/* Define this if you want DNS update functionality to be available. */

/* Enabling the DNS update functionality results in the creation of
   two UDP sockets with random high port numbers, but these numbers
   appear to ignore the configured net.ipv4.ip_local_port_range values.
   As a result, there's potential for collision with ports reserved
   for platform services.
   Given that this functionality is not being used, disable it from
   the build. */
#undef NSUPDATE

/* Define this if you aren't debugging and you want to save memory
   (potentially a _lot_ of memory) by allocating leases in chunks rather
   than one at a time. */

#define COMPACT_LEASES


/* local */
#define _PATH_DHCPD_CONF     "/etc/dhcp/dhcpd.conf"
#define _PATH_DHCLIENT_CONF  "/etc/dhcp/dhclient.conf"
