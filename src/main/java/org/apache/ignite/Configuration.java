package org.apache.ignite;

import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.Map;
import org.apache.ignite.configuration.DeploymentMode;
import org.apache.ignite.configuration.IgniteConfiguration;
import org.apache.ignite.internal.binary.BinaryMarshaller;
import org.apache.ignite.spi.discovery.tcp.TcpDiscoverySpi;
import org.apache.ignite.spi.discovery.tcp.ipfinder.vm.TcpDiscoveryVmIpFinder;

/**
 *
 */
public class Configuration {
    public static IgniteConfiguration getConfiguration(boolean submitter) {
        System.setProperty(IgniteSystemProperties.IGNITE_UPDATE_NOTIFIER, "false");
        System.setProperty(IgniteSystemProperties.IGNITE_NO_ASCII, "false");
        System.setProperty(IgniteSystemProperties.IGNITE_SUCCESS_FILE, "/dev/null");

        IgniteConfiguration cfg = new IgniteConfiguration();

        TcpDiscoveryVmIpFinder finder = new TcpDiscoveryVmIpFinder();
        finder.setAddresses(addresses());

        TcpDiscoverySpi disco = new TcpDiscoverySpi();
        disco.setIpFinder(finder);

        cfg.setDiscoverySpi(disco);
        cfg.setDeploymentMode(DeploymentMode.CONTINUOUS);
        cfg.setMarshalLocalJobs(true);
        cfg.setClassLoader(Configuration.class.getClassLoader());
        cfg.setIncludeProperties();
        cfg.setPublicThreadPoolSize(100);
        cfg.setSystemThreadPoolSize(16);
        cfg.setMarshaller(new BinaryMarshaller());
        cfg.setFailureDetectionTimeout(60_000);

        Map<String, Object> attrs = new HashMap<>();
        attrs.put("submitter", submitter);

        cfg.setUserAttributes(attrs);

        return cfg;
    }

    private static Collection<String> addresses() {
        String ips = System.getProperty("IGNITE_TEST_IPS");

        String[] addrs = ips.split(",");

        ArrayList<String> list = new ArrayList<>();

        for (String addr : addrs) {
            if (addr.length() > 0)
                list.add(addr);
        }

        return list;
    }
}
