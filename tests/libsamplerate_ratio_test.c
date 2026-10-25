/* Offline ratio contract regression for the retained libsamplerate copy.
 * Compile with its four C sources and -I pointing to that source directory.
 * Pass --finite to compare unchanged finite behavior against an older copy.
 */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "config.h"
#include "common.h"

static int callback_calls;
static long supply(void *opaque, float **data) {
    ++callback_calls;
    *data = opaque;
    return 0;
}
static void finite_controls(void) {
    const double valid[] = {1./256., .5, 1., 1.25, 2., 256.};
    const double invalid[] = {0., -0., -.5, -INFINITY, INFINITY,
                             nextafter(1./256., 0.), nextafter(256., INFINITY)};
    for (int type=SRC_ZERO_ORDER_HOLD; type<=SRC_LINEAR; ++type) {
        int error=-1;
        SRC_STATE *s=src_new(type,1,&error);
        assert(s && !error);
        float input[16], output[64];
        for (int i=0;i<16;++i) input[i]=(float)(i-7)/16.f;
        SRC_DATA d={.data_in=input,.data_out=output,.input_frames=16,
                    .output_frames=64,.end_of_input=1};
        assert(src_process(NULL,NULL)==SRC_ERR_BAD_STATE);
        assert(src_process(s,NULL)==SRC_ERR_BAD_DATA);
        for (unsigned i=0;i<sizeof(invalid)/sizeof(invalid[0]);++i) {
            d.src_ratio=invalid[i]; d.input_frames_used=17; d.output_frames_gen=19;
            assert(!src_is_valid_ratio(invalid[i]));
            assert(src_set_ratio(s,invalid[i])==SRC_ERR_BAD_SRC_RATIO);
            assert(src_process(s,&d)==SRC_ERR_BAD_SRC_RATIO);
            assert(d.input_frames_used==17 && d.output_frames_gen==19);
        }
        for (unsigned i=0;i<sizeof(valid)/sizeof(valid[0]);++i) {
            assert(src_is_valid_ratio(valid[i]));
            assert(src_reset(s)==0 && src_set_ratio(s,valid[i])==0);
            d.src_ratio=valid[i];
            assert(src_process(s,&d)==0);
            printf("finite type=%d ratio=%a used=%ld generated=%ld",type,valid[i],
                   d.input_frames_used,d.output_frames_gen);
            for (long j=0;j<d.output_frames_gen;++j) printf(" %a",(double)output[j]);
            puts("");
        }
        src_delete(s);
    }
}
static void nan_controls(void) {
    /* This assertion stops the baseline before any NaN processing call. */
    assert(src_is_valid_ratio(NAN)==0);
    int error=-1;
    SRC_STATE *s=src_new(SRC_LINEAR,1,&error); assert(s && !error);
    assert(src_set_ratio(s,.5)==0);
    float input[4]={1,2,3,4}, output[8]={0};
    SRC_DATA d={.data_in=input,.data_out=output,.input_frames=4,
                .output_frames=8,.input_frames_used=17,.output_frames_gen=19,
                .src_ratio=NAN};
    SRC_PRIVATE before=*(SRC_PRIVATE*)s;
    assert(src_set_ratio(s,NAN)==SRC_ERR_BAD_SRC_RATIO);
    assert(memcmp(&before,s,sizeof(before))==0);
    assert(src_process(NULL,&d)==SRC_ERR_BAD_STATE);
    assert(src_process(s,NULL)==SRC_ERR_BAD_DATA);
    d.data_in=NULL;
    assert(src_process(s,&d)==SRC_ERR_BAD_DATA_PTR);
    d.data_in=input;
    assert(src_process(s,&d)==SRC_ERR_BAD_SRC_RATIO);
    assert(d.input_frames_used==17 && d.output_frames_gen==19);
    assert(memcmp(&before,s,sizeof(before))==0);
    for(int i=0;i<8;++i) assert(output[i]==0);
    assert(input[0]==1 && input[3]==4);
    src_delete(s);
    s=src_callback_new(supply,SRC_LINEAR,1,&error,input); assert(s && !error);
    /* Wrong-mode error still takes precedence over the ratio error. */
    assert(src_process(s,&d)==SRC_ERR_BAD_MODE);
    assert(src_callback_read(s,NAN,0,output)==0 && src_error(s)==0);
    assert(src_callback_read(s,NAN,8,output)==0);
    assert(src_error(s)==SRC_ERR_BAD_SRC_RATIO && callback_calls==0);
    assert(((SRC_PRIVATE*)s)->mode==SRC_MODE_CALLBACK);
    assert(src_reset(s)==0 && src_error(s)==0);
    src_delete(s);
    puts("PASS NaN rejected via existing ratio error; validation order/state retained");
}
int main(int argc, char **argv) {
    if (argc==2 && strcmp(argv[1],"--finite")==0) {
        finite_controls();
        return 0;
    }
    nan_controls();
    finite_controls();
    return 0;
}
