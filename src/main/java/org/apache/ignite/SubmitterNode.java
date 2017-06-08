package org.apache.ignite;

import java.util.ArrayList;
import java.util.List;
import org.apache.ignite.cluster.ClusterGroup;
import org.apache.ignite.events.DiscoveryEvent;
import org.apache.ignite.events.Event;
import org.apache.ignite.events.EventType;
import org.apache.ignite.lang.IgniteCallable;
import org.apache.ignite.lang.IgniteFuture;
import org.apache.ignite.lang.IgnitePredicate;
import org.apache.ignite.lang.IgniteRunnable;

/**
 *
 */
public class SubmitterNode {
    public static void main(String[] args) throws InterruptedException {
        final int topSize = Integer.parseInt(args[0]);
        final int pause = Integer.parseInt(args[1]);
        final int jobs = Integer.parseInt(args[2]);

        final Ignite ignite = Ignition.start(Configuration.getConfiguration(true));

        ignite.events().enableLocal(EventType.EVT_NODE_JOINED);
        ignite.events().localListen(new IgnitePredicate<Event>() {
            @Override public boolean apply(Event evt) {
                DiscoveryEvent discoEvt = (DiscoveryEvent)evt;

                final int size = discoEvt.topologyNodes().size();

                if (topSize == size) {
                    new Thread() {
                        @Override public void run() {
                            IgniteCompute compute = null;

                            try {
                                ClusterGroup computeGrp = ignite.cluster().forAttribute("submitter", false);

                                compute = ignite.compute(computeGrp).withAsync();

                                List<IgniteFuture<Response>> futs = new ArrayList<>();

                                Thread.sleep(pause);

                                ignite.log().info("== Started submission, topSize=" + size
                                    + ", pause=" + pause + ", jobs=" + jobs);

                                for (int i = 0; i < jobs; i++) {
                                    compute.call(new TestCallable(new Bean1(String.valueOf(i), String.valueOf(i), i)));

                                    futs.add(compute.<Response>future());
                                }

                                for (IgniteFuture<Response> fut : futs)
                                    fut.get();
                            }
                            catch (InterruptedException e) {
                                e.printStackTrace();
                            }
                            finally {
                                if (compute != null) {
                                    compute.broadcast(new IgniteRunnable() {
                                        @Override public void run() {
                                            Ignition.localIgnite().close();
                                        }
                                    });

                                    ignite.close();
                                }

                            }

                        }
                    }.start();

                    return false;
                }

                return true;
            }
        }, EventType.EVT_NODE_JOINED);
    }

    /**
     *
     */
    private static class TestCallable implements IgniteCallable<Response> {
        /** Serial version uid. */
        private static final long serialVersionUID = -8827553917147806303L;
        /** */
        private Bean1 fld;

        /**
         * @param fld Field.
         */
        public TestCallable(Bean1 fld) {
            this.fld = fld;
        }

        /** {@inheritDoc} */
        @Override public Response call() throws Exception {
            Thread.sleep(10);
            return new Response(fld.fld1 + fld.fld2 + fld.fld3);
        }
    }

    /**
     *
     */
    private static class Bean1 {
        /** */
        private String fld1;

        /** */
        private String fld2;

        /** */
        private Integer fld3;

        /**
         * @param fld1 Fld 1.
         * @param fld2 Fld 2.
         * @param fld3 Fld 3.
         */
        public Bean1(String fld1, String fld2, Integer fld3) {
            this.fld1 = fld1;
            this.fld2 = fld2;
            this.fld3 = fld3;
        }
    }

    /**
     *
     */
    private static class Response {
        /** Fld. */
        private String fld;

        /**
         * @param fld Fld.
         */
        public Response(String fld) {
            this.fld = fld;
        }
    }

}
