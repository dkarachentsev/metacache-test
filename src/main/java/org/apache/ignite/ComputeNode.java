package org.apache.ignite;

/**
 *
 */
public class ComputeNode {
    public static void main(String[] args) {
        Ignition.start(Configuration.getConfiguration(false));
    }
}
