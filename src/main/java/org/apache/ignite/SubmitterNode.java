package org.apache.ignite;

import java.util.ArrayList;
import java.util.List;
import org.apache.ignite.cluster.ClusterGroup;
import org.apache.ignite.lang.IgniteCallable;
import org.apache.ignite.lang.IgniteFuture;
import org.apache.ignite.lang.IgniteRunnable;

/**
 *
 */
public class SubmitterNode {
    public static void main(String[] args) throws InterruptedException {
        Ignite ignite = Ignition.start(Configuration.getConfiguration(true));

        ClusterGroup computeGrp = ignite.cluster().forAttribute("submitter", false);

        IgniteCompute compute = ignite.compute(computeGrp).withAsync();

        List<IgniteFuture<Response>> futs = new ArrayList<>();

        Thread.sleep(10 * 1000);

        for (int i = 0; i < 400_000; i++) {
            compute.call(new TestCallable(new Bean1(String.valueOf(i), String.valueOf(i), i)));

            futs.add(compute.<Response>future());
        }

        for (IgniteFuture<Response> fut : futs)
            fut.get();

        compute.broadcast(new IgniteRunnable() {
            @Override public void run() {
                Ignition.localIgnite().close();
            }
        });

        ignite.close();
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
